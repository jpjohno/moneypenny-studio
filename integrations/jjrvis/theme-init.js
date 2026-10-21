/* Apply the saved palette before styles paint. Never requests user data. */
(function(){
 'use strict';
 let saved={};try{saved=JSON.parse(localStorage.getItem('jjrvis-display-v1')||'{}')||{};}catch{}
 const allowed=['midnight','sky','pearl','sage','lavender'];
 const choice=saved.appearance==='sky'&&saved.appearanceChosen!==true?'midnight':allowed.includes(saved.appearance)?saved.appearance:'midnight';
 const element=document.documentElement;element.dataset.appearance=choice;element.dataset.appearanceTone=choice==='midnight'?'dark':'light';
 element.style.colorScheme=choice==='midnight'?'dark':'light';
})();
