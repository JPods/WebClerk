// Temporary utility exports cloned from KanbanBoardPage for SvarGanttPage compatibility
export const DEFAULT_LANGUAGE_ORDER = ["en", "ar", "bn", "es"];
export const DIFFICULTY_OPTIONS = [1,2,3,5,8,13,21,34,55,101];
export const PROGRESS_OPTIONS = [0,5,30,50,70,90,100];
export const DEFAULT_DIFFICULTY = DIFFICULTY_OPTIONS[2];
export const DEFAULT_PROGRESS = PROGRESS_OPTIONS[0];
export const FALLBACK_COLUMN_ID = "column-uncategorized";
export const priorityOptions = ["low","medium","high","critical"];
export const PRIORITY_TO_VALUE = { low:1, medium:2, high:3, critical:4 };

export const getLanguageLabel = (code:string)=>({en:"English",ar:"Arabic",bn:"Bengali",es:"Spanish"}[code]||code);
export const normalizeLanguageCode=(c:string)=>c.trim().toLowerCase();
export const extendNumericOptionStrings=(opts:number[],cur:string)=>{
  const base=opts.map(String); return cur && !base.includes(cur)?[...base,cur]:base;
};
export const toTimestampMilliseconds=(v:string)=>{const d=new Date(v);return isNaN(d.getTime())?null:d.getTime()};
export const normalizeNumericSelectValue=(value:any,fallback:number)=>{
  const n=Number(value);return isNaN(n)?String(fallback):String(n);
};
export const calculateDueDate=(start:string,end:string)=>{
  const es=new Date(end); if(!isNaN(es.getTime())) return es.toISOString().slice(0,16);
  const ss=new Date(start); if(!isNaN(ss.getTime())){const d=new Date(ss);d.setDate(d.getDate()+1);return d.toISOString().slice(0,16);} return "";
};
export const createTranslationEntry=(language:string,title="",description="")=>({id:crypto.randomUUID(),language,title,description});
export const createTranslationEntriesFromTask=(task:any)=>{
  const codes=new Set<string>(); task.languageCodes?.forEach((c:string)=>codes.add(normalizeLanguageCode(c)));
  if(codes.size===0) codes.add("en");
  return [...codes].map(code=>createTranslationEntry(code,task.title||"",task.description||""));
};
export const createInitialTaskFormState=(columnId:string)=>({
  translations:[createTranslationEntry("en")],columnId,priority:"medium",dt_due:"",dt_start:"",dt_completed:"",dt_expected:"",
  assignee:"",difficulty:String(DEFAULT_DIFFICULTY),progress:String(DEFAULT_PROGRESS),percent_complete:"0"
});
export const findNextLanguageCode=(used:Set<string>,opts:any[])=>opts.find(o=>!used.has(o.value))?.value||"";
export const normalizeIncomingDateValue=(v:any)=>{const d=new Date(v);return isNaN(d.getTime())?"":d.toISOString().slice(0,16)};

export const updateTaskFormState=(prev:any,field:string,value:string)=>{
  const next={...prev,[field]:value}; return next;
};

// Re-export shared task utilities (correct source of truth)
export * from "../shared/taskFormUtils";

export default function KanbanGanttPage(){
  return null;
}
