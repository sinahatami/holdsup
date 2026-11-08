import { StepCard } from "@/components/molecules/step-card";
import { TitledSection } from "@/components/molecules/titled-section";
import { strings } from "@/lib/strings";

export function HowItWorks() {
  return (
    <TitledSection
      id="how"
      title={strings.home.howHeading}
      className="scroll-mt-24"
    >
      <ol className="grid gap-4 sm:grid-cols-3">
        {strings.home.how.map((step, i) => (
          <StepCard
            key={step.title}
            number={i + 1}
            title={step.title}
            body={step.body}
          />
        ))}
      </ol>
    </TitledSection>
  );
}
