import BN from 'bn.js';

export function shortHex(decString) {
  if (!decString) return '';
  try {
    const bnVal = new BN(decString.trim(), 10);
    let hex = bnVal.toString(16);
    if (hex.length <= 12) {
      return '0x' + hex; 
    }
    const firstPart = hex.slice(0, 8);
    const lastPart = hex.slice(-4);
    return `0x${firstPart}...${lastPart}`;
  } catch (err) {
    return decString;
  }
}

