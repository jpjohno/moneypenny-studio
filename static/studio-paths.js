export function normaliseStudioBase(value){return value==='/presence/'||value==='/presence'?'/presence/':'/';}
export const STUDIO_BASE=normaliseStudioBase(globalThis.document?.querySelector('meta[name="studio-base"]')?.content);
export function studioURL(path,base=STUDIO_BASE){return typeof path==='string'&&path.startsWith('/')&&!path.startsWith('//')&&base!=='/'?base+path.slice(1):path;}
export function studioFetch(input,options){return globalThis.fetch(studioURL(input),options);}
export function parentOrigins(base=STUDIO_BASE,origin=globalThis.location?.origin){return ['http://127.0.0.1:8766','http://localhost:8766',...(base==='/presence/'&&origin?[origin]:[])];}
