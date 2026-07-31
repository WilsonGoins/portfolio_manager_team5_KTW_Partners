// A holding's type reaches the UI in two different shapes. Every display site
// runs the value through here. Keyed on the uppercased value, so either form in
// gives the same label out.
const TYPE_LABELS = {
  EQUITY: 'Equity',
  ETF: 'ETF',
  MUTUALFUND: 'Mutual Fund',
  INDEX: 'Index',
  CRYPTOCURRENCY: 'Crypto',
  CURRENCY: 'Currency',
  FUTURE: 'Future',
  OPTION: 'Option',
  CASH: 'Cash',
};

export function formatHoldingType(value) {
  // cash rows carry "--" for the fields that don't apply to them, and a missing
  // type should pass through looking the way the rest of the row's blanks do
  if (value === null || value === undefined || value === '') return '--';

  const key = String(value).trim().toUpperCase();
  if (TYPE_LABELS[key]) return TYPE_LABELS[key];
  if (key === '--') return '--';

  // Something new from Yahoo. Short ones are acronyms and are left alone; longer
  // ones read better as a word than as shouting.
  return key.length <= 4 ? key : key.charAt(0) + key.slice(1).toLowerCase();
}
