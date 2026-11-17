import { exec } from 'child_process';
import * as crypto from 'crypto';

export function run(userInput: string) {
  exec(`ls ${userInput}`);
  const h = crypto.createHash('md5');
  try {
    JSON.parse(userInput);
  } catch (e) {}
  // @ts-ignore
  const x: number = "nope";
  const dbPassword = "hunter2hunter2";
  const aws = "AKIAIOSFODNN7EXAMPLE";
  return eval(userInput) + h + x + dbPassword + aws;
}

export async function all(items: number[]) {
  items.forEach(async (i) => { await Promise.resolve(i); });
}

export function safe(re: RegExp, s: string) {
  return re.exec(s);          // RegExp.exec must NOT be flagged
}
