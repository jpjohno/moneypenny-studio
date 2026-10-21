const negate=/\b(?:don't|do not|avoid|without|stop)\b/i;
export const actionOnly=text=>!negate.test(text)&&!/\b(?:what|why|how|where|when|who|which|explain|tell me|recommend)\b/i.test(text);
const labels={bend_forward:'bend forward',supported_step:'put one foot on the seat',lie_back:'lie on my back',reach:'reach',jig:'dance a jig',dance:'dance',walk:'walk',turn:'turn',stretch:'stretch',bow:'bow',sit:'sit',kneel:'kneel',splits:'try the splits pose',custom:'perform the saved movement',idle:'relax'};
export function movementAcknowledgement(plan){
  const steps=plan.steps.map(step=>step.skill==='reach'?`reach towards my ${step.target==='belly'?'belly button':step.target}`:labels[step.skill]||'perform the movement');
  return `I’ll ${steps.join(', then ')} now.`;
}
export function wardrobeCommand(text){
  if(negate.test(text))return null;
  const result={};
  const remove=/\b(?:remove|take off)\s+(?:(?:your|the|my)\s+)?(?:jacket|waistcoat|dress|outer layers?|outer clothes)\b/i.test(text);
  const wear=/\b(?:wear|put on|change into|change (?:your |my )?(?:outfit|clothes))\b/i.test(text);
  if(remove)result.outfit='base';
  else if(wear){
    if(/\b(?:office|business|waistcoat|jacket)\b/i.test(text))result.outfit='office';
    else if(/\b(?:casual|trousers|jeans)\b/i.test(text))result.outfit='casual';
    else if(/\b(?:dress|evening)\b/i.test(text))result.outfit='dress';
  }
  if(wear){
    if(/\b(?:trainers|sneakers)\b/i.test(text))result.footwear='trainers';
    else if(/\bheels\b/i.test(text))result.footwear='heels';
    else if(/\bflats\b/i.test(text))result.footwear='flats';
  }
  return Object.keys(result).length?result:null;
}
