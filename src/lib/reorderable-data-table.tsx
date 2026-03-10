import React, { useCallback, useMemo, useRef, useState } from "react";
import DataTableBase, {
  TableColumn,
  TableProps,
} from "react-data-table-component/dist/index.es.js";
import { DndProvider, useDrag, useDrop } from "react-dnd";
import { HTML5Backend } from "react-dnd-html5-backend";
import { FaGripVertical } from "react-icons/fa";

// Draggable header cell used to reorder columns
const DraggableHeader: React.FC<{
  index: number;
  move: (from: number, to: number) => void;
  children: React.ReactNode;
}> = ({ index, move, children }) => {
  const ref = useRef<HTMLDivElement | null>(null);

  const [, drop] = useDrop({
    accept: "rdt-column",
    hover(item: { index: number }, monitor) {
      if (!ref.current) return;
      const dragIndex = item.index;
      const hoverIndex = index;
      if (dragIndex === hoverIndex) return;

      const hoverRect = ref.current.getBoundingClientRect();
      const hoverMiddleX = (hoverRect.right - hoverRect.left) / 2;
      const clientOffset = monitor.getClientOffset();
      if (!clientOffset) return;
      const hoverClientX = clientOffset.x - hoverRect.left;

      if (dragIndex < hoverIndex && hoverClientX < hoverMiddleX) return;
      if (dragIndex > hoverIndex && hoverClientX > hoverMiddleX) return;

      move(dragIndex, hoverIndex);
      item.index = hoverIndex;
    },
  });

  const [{ isDragging }, drag] = useDrag({
    type: "rdt-column",
    item: { index },
    collect: (monitor) => ({ isDragging: monitor.isDragging() }),
  });

  drag(drop(ref));

  return (
    <div
      ref={ref}
      className="flex items-center gap-2 select-none"
      style={{ cursor: "move", opacity: isDragging ? 0.6 : 1 }}
    >
      <FaGripVertical size={12} className="text-white" />
      <span className="truncate">{children}</span>
    </div>
  );
};

const addIds = <T,>(cols: TableColumn<T>[]): TableColumn<T>[] => {
  return cols.map((col, idx) => ({
    id: col.id ?? String(col.name ?? col.selector ?? idx),
    sortable: col.sortable ?? true,
    ...col,
  }));
};

function ReorderableDataTable<T extends Record<string, unknown>>(
  props: TableProps<T>,
) {
  const { columns: incomingColumns, ...rest } = props;
  const [columns, setColumns] = useState<TableColumn<T>[]>(() =>
    addIds(incomingColumns),
  );

  React.useEffect(() => {
    setColumns(addIds(incomingColumns));
  }, [incomingColumns]);

  const moveColumn = useCallback((from: number, to: number) => {
    setColumns((prev) => {
      const next = [...prev];
      const [dragged] = next.splice(from, 1);
      next.splice(to, 0, dragged);
      return next;
    });
  }, []);

  const decoratedColumns = useMemo(() => {
    return columns.map((col, index) => ({
      ...col,
      name: (
        <DraggableHeader index={index} move={moveColumn}>
          {col.name}
        </DraggableHeader>
      ),
    }));
  }, [columns, moveColumn]);

  return (
    <DndProvider backend={HTML5Backend}>
      <DataTableBase {...rest} columns={decoratedColumns} />
    </DndProvider>
  );
}

export type { TableColumn, TableProps };
export default ReorderableDataTable;
