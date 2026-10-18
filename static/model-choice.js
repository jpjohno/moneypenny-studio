export const DOLPHIN_MODEL='cognitivecomputations/dolphin-llama3:latest';

export function chooseModel(models,saved){
  if(models.includes(saved))return saved;
  return [DOLPHIN_MODEL,'dolphin-llama3:latest','uncensored-3b:latest','MoneyPenny:latest',...models].find(name=>models.includes(name))||'';
}
