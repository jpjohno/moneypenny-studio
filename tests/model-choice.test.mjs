import test from 'node:test';
import assert from 'node:assert/strict';
import {chooseModel,DOLPHIN_MODEL} from '../static/model-choice.js';

test('fresh studio uses installed Dolphin without downloading or guessing tags',()=>{
  assert.equal(chooseModel(['uncensored-3b:latest',DOLPHIN_MODEL]),DOLPHIN_MODEL);
  assert.equal(chooseModel(['dolphin-llama3:latest']), 'dolphin-llama3:latest');
});
test('saved model selection is respected including the original MoneyPenny tag',()=>{
  for(const saved of ['MoneyPenny:latest','uncensored-3b:latest'])assert.equal(chooseModel([DOLPHIN_MODEL,saved],saved),saved);
});
test('removed models fall back to installed choices and an empty list stays empty',()=>{
  assert.equal(chooseModel(['local:latest'],'removed:latest'),'local:latest');
  assert.equal(chooseModel([]),'');
});
