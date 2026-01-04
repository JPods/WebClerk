import { getRecords, saveRecord, deleteRecord, getRecord } from '../../../../../api/wcapi';
import { patchAction } from '../../../../../api/userProfile';
import {
  SalesOrderLine,
  CreateSalesOrderLineRequest,
  UpdateSalesOrderLineRequest
} from '../types/salesOrderLineType';

export const fetchSalesOrders = async (params?: any) => {
  const res = await getRecords('salesorder', params);
  return { status: 200, data: { items: res.results || [] } };
};

export const createSalesOrder = async (data: any) => {
  return saveRecord('salesorder', data);
};

export const updateSalesOrder = async (id: number, data: any) => {
  return saveRecord('salesorder', { ...data, id });
};

export const deleteSalesOrder = async (id: number) => {
  return deleteRecord('salesorder', id);
};

// Sales Order Lines API
export const fetchSalesOrderLines = async (salesOrderId: number): Promise<{ status: number; data: { results: SalesOrderLine[]; total: number } }> => {
  const res = await getRecords('sales_order_line', { parent: salesOrderId });
  return { status: 200, data: { results: res.results || [], total: res.total || 0 } };
};

export const createSalesOrderLine = async (salesOrderId: number, data: CreateSalesOrderLineRequest): Promise<{ status: number; data: SalesOrderLine }> => {
  const payload = {
    model_name: 'sales_order_line',
    ...data,
    parent: salesOrderId,
  };
  const res = await patchAction(payload);
  return { status: res?.status || 200, data: res?.data || res };
};

export const updateSalesOrderLine = async (salesOrderId: number, lineId: number, data: UpdateSalesOrderLineRequest): Promise<{ status: number; data: SalesOrderLine }> => {
  const payload = {
    model_name: 'sales_order_line',
    ...data,
    parent: salesOrderId,
    id: lineId,
  };
  const res = await patchAction(payload);
  return { status: res?.status || 200, data: res?.data || res };
};

export const deleteSalesOrderLine = async (_salesOrderId: number, lineId: number): Promise<{ status: number; data: any }> => {
  const payload = {
    model_name: 'sales_order_line',
    id: lineId,
    method: 'delete',
  };
  const res = await patchAction(payload);
  return { status: res?.status || 200, data: res?.data || res };
};

export const fetchSalesOrderDetail = async (id: number): Promise<any> => {
  const res = await getRecord('salesorder', id);
  return res?.record ?? res;
};