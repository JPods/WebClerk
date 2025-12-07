import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import ComponentCard from "../../../../../components/common/ComponentCard";
import Label from "../../../../../components/form/Label";
import { Input } from "../../../../../components/wrapper";
import { ProposalLine } from "../types/proposalLineType";

// Simple schema for proposal line - can be expanded
const proposalLineSchema = z.object({
  item_description: z.string().optional(),
  quantity_placed: z.number().optional(),
  price_unit: z.number().optional(),
  cost_unit: z.number().optional(),
});

interface ProposalLineDetailProps {
  proposalId: number;
  line?: ProposalLine;
  mode: "add" | "edit" | "view";
  onSave?: (data: any) => void;
  onCancel?: () => void;
}

export default function ProposalLineDetail({
  proposalId,
  line,
  mode,
  onSave,
  onCancel
}: ProposalLineDetailProps) {
  const {
    register,
    handleSubmit,
    setValue,
  } = useForm({
    resolver: zodResolver(proposalLineSchema),
  });

  // Set form values when editing
  useEffect(() => {
    if (line && mode === "edit") {
      setValue("item_description", line.item?.description || "");
      setValue("quantity_placed", line.quantity?.placed || 0);
      setValue("price_unit", line.price?.unit || 0);
      setValue("cost_unit", line.cost?.unit || 0);
    }
  }, [line, mode, setValue]);

  const onSubmit = (data: any) => {
    if (onSave) {
      onSave({ ...data, proposalId });
    }
  };

  return (
    <ComponentCard>
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold">
          {mode === "edit" ? "Edit Proposal Line" : mode === "view" ? "View Proposal Line" : "Add Proposal Line"}
        </h3>
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="text-gray-500 hover:text-gray-700"
          >
            &times;
          </button>
        )}
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <Label htmlFor="item_description">Item Description</Label>
            <Input
              type="text"
              id="item_description"
              placeholder="Item description"
              {...register("item_description")}
              disabled={mode === "view"}
            />
          </div>
          <div>
            <Label htmlFor="quantity_placed">Quantity</Label>
            <Input
              type="number"
              id="quantity_placed"
              placeholder="Quantity"
              {...register("quantity_placed", { valueAsNumber: true })}
              disabled={mode === "view"}
            />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <Label htmlFor="price_unit">Unit Price</Label>
            <Input
              type="number"
              step="0.01"
              id="price_unit"
              placeholder="Unit price"
              {...register("price_unit", { valueAsNumber: true })}
              disabled={mode === "view"}
            />
          </div>
          <div>
            <Label htmlFor="cost_unit">Unit Cost</Label>
            <Input
              type="number"
              step="0.01"
              id="cost_unit"
              placeholder="Unit cost"
              {...register("cost_unit", { valueAsNumber: true })}
              disabled={mode === "view"}
            />
          </div>
        </div>

        {mode !== "view" && (
          <div className="flex items-center gap-2">
            <button
              type="submit"
              className="flex items-center px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600"
            >
              {mode === "edit" ? "Update" : "Save"}
            </button>
            {onCancel && (
              <button
                type="button"
                onClick={onCancel}
                className="flex items-center px-4 py-2 text-gray-700 bg-gray-200 rounded-md hover:bg-gray-300"
              >
                Cancel
              </button>
            )}
          </div>
        )}
      </form>
    </ComponentCard>
  );
}