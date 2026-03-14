/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { useMemo } from "react";
import { FieldError, useForm } from "react-hook-form";
import ComponentCard from "../../common/ComponentCard";
import TextArea from "../input/TextArea";
import Label from "../Label";

type TextAreaSampleForm = {
  description: string;
  disabledDescription: string;
  errorDescription: string;
};

export default function TextAreaInput() {
  const { register } = useForm<TextAreaSampleForm>({
    defaultValues: {
      description: "",
      disabledDescription: "",
      errorDescription: "",
    },
  });

  const staticError = useMemo<FieldError>(
    () => ({ type: "manual", message: "Please enter a valid message." }),
    []
  );

  return (
    <ComponentCard title="Textarea input field">
      <div className="space-y-6">
        {/* Default TextArea */}
        <div>
          <Label>Description</Label>
          <TextArea rows={6} register={register("description")} />
        </div>

        {/* Disabled TextArea */}
        <div>
          <Label>Description</Label>
          <TextArea rows={6} disabled register={register("disabledDescription")} />
        </div>

        {/* Error TextArea */}
        <div>
          <Label>Description</Label>
          <TextArea
            rows={6}
            register={register("errorDescription")}
            error={staticError}
            hint={staticError.message}
          />
        </div>
      </div>
    </ComponentCard>
  );
}
