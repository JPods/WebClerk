/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * useDragAndDrop - Custom hook for drag and drop reordering
 * Uses HTML5 Drag and Drop API for simple list reordering
 */
import { useState, useCallback, useRef } from 'react';

interface UseDragAndDropOptions<T> {
  items: T[];
  onReorder: (items: T[]) => void;
  idKey?: keyof T;
}

interface DragState {
  isDragging: boolean;
  dragIndex: number | null;
  dropIndex: number | null;
}

export function useDragAndDrop<T>({
  items,
  onReorder,
  idKey = 'id' as keyof T,
}: UseDragAndDropOptions<T>) {
  const [dragState, setDragState] = useState<DragState>({
    isDragging: false,
    dragIndex: null,
    dropIndex: null,
  });
  
  const draggedItem = useRef<T | null>(null);

  const handleDragStart = useCallback((index: number, e: React.DragEvent) => {
    draggedItem.current = items[index];
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', String(index));
    
    // Set drag image (optional styling)
    const target = e.currentTarget as HTMLElement;
    if (target) {
      e.dataTransfer.setDragImage(target, 20, 20);
    }
    
    setDragState({
      isDragging: true,
      dragIndex: index,
      dropIndex: null,
    });
  }, [items]);

  const handleDragOver = useCallback((index: number, e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    
    setDragState(prev => ({
      ...prev,
      dropIndex: index,
    }));
  }, []);

  const handleDragEnter = useCallback((index: number, e: React.DragEvent) => {
    e.preventDefault();
    setDragState(prev => ({
      ...prev,
      dropIndex: index,
    }));
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
  }, []);

  const handleDrop = useCallback((index: number, e: React.DragEvent) => {
    e.preventDefault();
    
    const dragIndex = parseInt(e.dataTransfer.getData('text/plain'), 10);
    
    if (dragIndex === index) {
      setDragState({
        isDragging: false,
        dragIndex: null,
        dropIndex: null,
      });
      return;
    }
    
    // Reorder items
    const newItems = [...items];
    const [draggedItemData] = newItems.splice(dragIndex, 1);
    newItems.splice(index, 0, draggedItemData);
    
    onReorder(newItems);
    
    setDragState({
      isDragging: false,
      dragIndex: null,
      dropIndex: null,
    });
    
    draggedItem.current = null;
  }, [items, onReorder]);

  const handleDragEnd = useCallback(() => {
    setDragState({
      isDragging: false,
      dragIndex: null,
      dropIndex: null,
    });
    draggedItem.current = null;
  }, []);

  // Get drag props for an item at a given index
  const getDragProps = useCallback((index: number) => ({
    draggable: true,
    onDragStart: (e: React.DragEvent) => handleDragStart(index, e),
    onDragOver: (e: React.DragEvent) => handleDragOver(index, e),
    onDragEnter: (e: React.DragEvent) => handleDragEnter(index, e),
    onDragLeave: handleDragLeave,
    onDrop: (e: React.DragEvent) => handleDrop(index, e),
    onDragEnd: handleDragEnd,
  }), [handleDragStart, handleDragOver, handleDragEnter, handleDragLeave, handleDrop, handleDragEnd]);

  // Get styling classes for an item
  const getDragClasses = useCallback((index: number) => {
    const { isDragging, dragIndex, dropIndex } = dragState;
    
    if (!isDragging) return '';
    
    const classes: string[] = [];
    
    if (dragIndex === index) {
      classes.push('opacity-50', 'bg-blue-50', 'dark:bg-blue-900/20');
    }
    
    if (dropIndex === index && dragIndex !== index) {
      classes.push('border-t-2', 'border-blue-500');
    }
    
    return classes.join(' ');
  }, [dragState]);

  return {
    dragState,
    getDragProps,
    getDragClasses,
  };
}

export default useDragAndDrop;
