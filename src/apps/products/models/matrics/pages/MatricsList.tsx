import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../components/common/ComponentCard";
import AdvancedDataTable from "../../../../../components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback, useMemo } from "react";
import { deleteAction } from "../../../../../api/userProfile";
import { fetchMatricss } from "../services/matricsApi";
import { FaEye, FaEdit, FaPlus, FaTrash } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import MatricsDetail from "./MatricsDetail";

export default function MatricsList() {
  const dispatch = useDispatch();
  const [data, setData] = useState<any[]>([]);
  const [selectedMatrics, setSelectedMatrics] = useState<any | null>(nullimport PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../compadimport ComponentCard from "../../../../../components/common/ComponentCard";
(fimport AdvancedDataTable from "../../../../../components/common/AdvancedDa simport { TableColumn } from "react-data-table-component";
import { useEffect, useS 2import { useEffect, useState, useCallback, useMemo } froe import { deleteAction } from "../../../../../api/userProfile";
im, import { fetchMatricss } from "../services/matricsApi";
impore.import { FaEye, FaEdit, FaPlus, FaTrash } from "react-h(import { showToast } from "../../../../../store/slices/toastSli))import { useDispatch } from "react-redux";
import MatricsDetail fr

import MatricsDetail from "./MatricsDetai
 
export default function MatricsList() {
  = u  const dispatch any) => {
    setSelect  const [data, setData] = useSta"v  const [selectedMatrics, setSelectedMatrics]lbimport ComponentCard from "../../../../../compadimport ComponentCard from "../../../../../components/common/ComponentCard";
(fimport AdvancedDataTabltF(fimport AdvancedDataTable from "../../../../../components/common/AdvancedDa simport { TableColumn } from "react-data-tabls(import { useEffect, useS 2import { useEffect, useState, useCallback, useMemo } froe import { deleteAction } from "../../../../../api/ualim, import { fetchMatricss } from "../services/matricsApi";
impore.import { FaEye, FaEdit, FaPlus, FaTrash } from "react-h(import { showToast } f  impore.import { FaEye, FaEdit, FaPlus, FaTrash } from "reaulimport MatricsDetail fr

import MatricsDetail from "./MatricsDetai
 
export default function MatricsList() {
  = u  const dispatch any) => {
    setSelect  const [data, sp
import MatricsDetail ;

  const handleBulkDelete = useCallback(async  = u  const dispatch any) => {
    sele    setSelect  const [data, seco(fimport AdvancedDataTabltF(fimport AdvancedDataTable from "../../../../../components/common/AdvancedDa simport { TableColumn } from "react-data-tabls(import { useEffect, useS 2import { useEffect, useState, useCallbaleimpore.import { FaEye, FaEdit, FaPlus, FaTrash } from "react-h(import { showToast } f  impore.import { FaEye, FaEdit, FaPlus, FaTrash } from "reaulimport MatricsDetail fr

import MatricsDetail from "./MatricsDetai
 
export default function MatricsList() {
  = u  const dispatch any) => {
    setSelect  const [data, sp
import MatricsDetail ;

   n
import MatricsDetail from "./MatricsDetai
 
export default function MatricsList() {
  = u  const dispatch any) => {
    setSelect  const [data, sp
import MatricsDetail },
 
export default function MatricsList() or:   = u  const dispatch any) => {
    setr    setSelect  const [data, sp"uimport MatricsDetail ;

  con (
  const handleBulkDe--"    sele    setSelect  const [data, seco(fimport AdvancedDataTabltF(fimporio
import MatricsDetail from "./MatricsDetai
 
export default function MatricsList() {
  = u  const dispatch any) => {
    setSelect  const [data, sp
import MatricsDetail ;

   n
import MatricsDetail from "./MatricsDetai
 
export default function MatricsList() {
  = u  const dispatch any) => {
    setSelect  const [data, sp
import MatricsDetail },
 
export default function MatricsList() or:   = u  const dispatch any) => {
   aEd 
export default function MatricsList() -110  = u  const dispatch any) => {
    se        <button onClick={() => hanimport MatricsDetail ;

   n
">
   n
import MatricsD climpNa 
export default function MatricsList() ion"  = u  const dispatch any) => {
    se
     setSelect  const [data, sptrimport MatricsDetail },
 
exp,
 
export default funct        setr    setSelect  const [data, sp"uimport MatricsDetail ;

  con (
re
  con (
  const handleBulkDe--"    sele    setSelect  const />
      <dimport MatricsDetail from "./MatricsDetai
 
export default function MatricsList() {
  = u  const dpa 
export default fu-3"}>
          <Componen  = u  const dispatch any) => {
    se      setSelect  const [data, sp  import MatricsDetail ;

       
   n
import MatricsD"
 imp   
export default function MatricsList() stor  = u  const dispatch any) => {
    seab    setSelect  const [data, spenimport MatricsDetail },
 
exp   
export default funct{set   aEd 
export default function MatricsList() -110  = u  const dispatch   export o    se        <button onClick={() => hanimport MatricsDetail ;

   ntrics.
   n
">
   n
import MatricsD climpNa 
export default functi    ">
st mAimpons={
                <div     se
     setSelect  const [data, sptrimport MatricsDetail },
 
exp,
 0 && (
   
exp,
 
export default funct        setr    setSelect ={ha 
eeBul
  con (
re
  con (
  const handleBulkDe--"    sele    setSelect  const />
      <dim fore
  cium t  consit      <dimport MatricsDetail from "./MatricsDetai
 
eol 
export default function MatricsList() {
  = u  <Fa  = u  const me="w-4 h-4" />
           export default fe           <Componen  .l    se      setSelect  const [data, sp  import     
       
   n
import MatricsD"
 imp   
export default functio={h   n
iddimp   imp   
export   exportam    seab    setSelect  const [data, spenimport MatricsDetail },
 
exp   -b 
exp   
export default funct{set   aEd 
export default functi    expor  export default functio <FaPlus c
   ntrics.
   n
">
   n
import MatricsD climpNa 
export default functi    ">
st mAimpons={
                <div     se}
            />
     n
">
 /Compon ntCard>export default functi   {st mAimpons={
            iv            lg     setSelect  const [dat<M 
exp,
 0 && (
   
exp,
 
export default funct        sp={f 0 Mo   
ex  ex   
e   deeBul
  con (
re
  con (
  const handleBulkDe--"  andleForre
  c}
                 <dim fore
  cium t  consit      <dimport Matric    cium t  cons   
eol 
export default fun </>
  );
}
