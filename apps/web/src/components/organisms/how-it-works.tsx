import Link from "next/link";
import { StepCard } from "@/components/molecules/step-card";
import { TitledSection } from "@/components/molecules/titled-section";
import { routes } from "@/lib/routes";
import { strings } from "@/lib/strings";

export function HowItWorks() {
  return (
    <TitledSection
      id="how"
      title={strings.home.howHeading}
      className="scroll-mt-24"
    >
      <ol className="grid gap-4 md:grid-cols-3">
        {strings.home.how.map((step, i) => (
          <StepCard
            key={step.title}
            number={i + 1}
            title={step.title}
            body={step.body}
            exampleLabel={strings.home.howExampleLabel}
            example={step.example}
          />
        ))}
      </ol>
      <p>
        <Link
          href={routes.methodology}
          className="text-brand font-medium underline underline-offset-4"
        >
          {strings.home.howMore}
        </Link>
      </p>
    </TitledSection>
  );
}
