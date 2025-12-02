export interface CatalogAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateCatalogRequest {
  name: string;
  description: string;
  category: string;
  price?: number;
}

export interface CatalogApiTask {
  id: number;
  uuid: string | null;
  name: string;
  description: string;
  category: string;
  price?: number;
  dt_created?: number;
  dt_modified?: number;
  version?: number;
  is_active?: boolean;
}

export interface UpdateCatalogRequest {
  id: number;
  name: string;
  description: string;
  category: string;
  price?: number;
}