#!/usr/bin/env bash
# One-time setup that lets .github/workflows/cd.yml deploy the API to Cloud Run without a
# stored key (DEPLOY.md, section 4; D042). Run it yourself: `make deploy-setup GCP_PROJECT=…`,
# with gcloud signed in as the project's owner and gh signed in to the repository.
# Running it again is safe: it keeps what exists and resets the provider's condition.
#
# It creates:
#   - a Workload Identity pool `github` with a provider `holdsup` that accepts GitHub's OIDC
#     tokens only from cd.yml on this repository's main branch;
#   - a service account `holdsup-deployer` that may push images to the `holdsup` repository,
#     deploy the `holdsup-api` service and run it as its current runtime account, and nothing
#     else in the project;
#   - four repository variables (not secrets: none of them is a key) that cd.yml reads.
set -euo pipefail

project=${1:?usage: setup-deploy.sh <project id> [region]}
region=${2:-us-east4}
service=holdsup-api # API_SERVICE in the Makefile
images=holdsup      # the Artifact Registry repository (DEPLOY.md, section 2)
pool=github
provider=holdsup
deployer="holdsup-deployer@$project.iam.gserviceaccount.com"

number=$(gcloud projects describe "$project" --format='value(projectNumber)')
repo=$(gh repo view --json nameWithOwner --jq .nameWithOwner)
repo_id=$(gh api "repos/$repo" --jq .id)
runtime=$(gcloud run services describe "$service" --project "$project" --region "$region" \
  --format='value(spec.template.spec.serviceAccountName)')
pool_path="projects/$number/locations/global/workloadIdentityPools/$pool"

echo "Project $project ($number), region $region, repository $repo ($repo_id)."
echo "$service runs as $runtime."

# A newly created service account can take a few seconds to show up in IAM.
retry() {
  local attempt
  for attempt in 1 2 3 4 5 6; do
    if "$@"; then return 0; fi
    echo "  (retrying in 10 s, attempt $attempt of 6)"
    sleep 10
  done
  return 1
}

echo "Enabling the token exchange APIs."
gcloud services enable iamcredentials.googleapis.com sts.googleapis.com --project "$project"

if ! gcloud iam workload-identity-pools describe "$pool" --project "$project" \
  --location global >/dev/null 2>&1; then
  echo "Creating the Workload Identity pool $pool."
  gcloud iam workload-identity-pools create "$pool" --project "$project" --location global \
    --display-name GitHub
fi

mapping='google.subject=assertion.sub,attribute.repository_id=assertion.repository_id'
condition="assertion.repository_id == '$repo_id' && assertion.ref == 'refs/heads/main'"
condition+=" && assertion.job_workflow_ref == '$repo/.github/workflows/cd.yml@refs/heads/main'"
if gcloud iam workload-identity-pools providers describe "$provider" --project "$project" \
  --location global --workload-identity-pool "$pool" >/dev/null 2>&1; then
  echo "Updating the provider $provider."
  gcloud iam workload-identity-pools providers update-oidc "$provider" --project "$project" \
    --location global --workload-identity-pool "$pool" \
    --attribute-mapping "$mapping" --attribute-condition "$condition"
else
  echo "Creating the provider $provider."
  gcloud iam workload-identity-pools providers create-oidc "$provider" --project "$project" \
    --location global --workload-identity-pool "$pool" \
    --issuer-uri https://token.actions.githubusercontent.com \
    --attribute-mapping "$mapping" --attribute-condition "$condition"
fi

if ! gcloud iam service-accounts describe "$deployer" --project "$project" >/dev/null 2>&1; then
  echo "Creating the service account $deployer."
  gcloud iam service-accounts create "${deployer%%@*}" --project "$project" \
    --display-name "API deploys from GitHub (cd.yml)"
fi

echo "Granting it the image repository, the service and the runtime account only."
retry gcloud artifacts repositories add-iam-policy-binding "$images" --project "$project" \
  --location "$region" --member "serviceAccount:$deployer" \
  --role roles/artifactregistry.writer --format none
retry gcloud run services add-iam-policy-binding "$service" --project "$project" \
  --region "$region" --member "serviceAccount:$deployer" \
  --role roles/run.developer --format none
retry gcloud iam service-accounts add-iam-policy-binding "$runtime" --project "$project" \
  --member "serviceAccount:$deployer" \
  --role roles/iam.serviceAccountUser --format none

echo "Letting this repository's runs act as it (the provider narrows that to cd.yml on main)."
retry gcloud iam service-accounts add-iam-policy-binding "$deployer" --project "$project" \
  --member "principalSet://iam.googleapis.com/$pool_path/attribute.repository_id/$repo_id" \
  --role roles/iam.workloadIdentityUser --format none

echo "Setting the repository variables cd.yml reads."
gh variable set GCP_PROJECT --repo "$repo" --body "$project"
gh variable set GCP_REGION --repo "$repo" --body "$region"
gh variable set GCP_DEPLOY_SERVICE_ACCOUNT --repo "$repo" --body "$deployer"
gh variable set GCP_WORKLOAD_IDENTITY_PROVIDER --repo "$repo" --body "$pool_path/providers/$provider"

echo
echo "Done. On GitHub, open Actions → Deploy API → Run workflow (branch main) once to check it."
