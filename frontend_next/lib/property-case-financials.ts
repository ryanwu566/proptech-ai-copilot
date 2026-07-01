export type FundingMode = "loan_amount" | "down_payment";
export type FinancialMetricStatus = "available" | "incomplete" | "unavailable";

export type FinancialMetric = {
  status: FinancialMetricStatus;
  value: number | null;
  message: string;
};

export type PropertyCaseFinancialInputs = {
  listingPrice: number | null;
  userEstimatedValue: number | null;
  fundingMode: FundingMode;
  fundingValue: number | null;
  annualInterestRate: number | null;
  loanYears: number | null;
  estimatedBuyerCosts: number | null;
  renovationReserve: number | null;
  availableLiquidCash: number | null;
  monthlyHouseholdIncome: number | null;
  monthlyFixedObligations: number | null;
  monthlyOwnershipReserve: number | null;
};

export type PropertyCaseFinancialScenarioInput = {
  scenarioName: string;
  optionalListingPrice: number | null;
  optionalAnnualInterestRate: number | null;
  optionalEstimatedBuyerCosts: number | null;
  optionalRenovationReserve: number | null;
  optionalMonthlyHouseholdIncome: number | null;
  optionalMonthlyFixedObligations: number | null;
  optionalMonthlyOwnershipReserve: number | null;
};

export type PropertyCaseFinancialAnalysis = {
  fundingMode: FundingMode;
  listingPrice: FinancialMetric;
  userEstimatedValue: FinancialMetric;
  loanAmount: FinancialMetric;
  downPayment: FinancialMetric;
  totalCommitment: FinancialMetric;
  cashNeeded: FinancialMetric;
  monthlyPayment: FinancialMetric;
  monthlyBurden: FinancialMetric;
  monthlyResidual: FinancialMetric;
  postPurchaseCash: FinancialMetric;
  ltvRatio: FinancialMetric;
  userValueGap: FinancialMetric;
  warnings: string[];
  isReadyForScenarioComparison: boolean;
};

export type PropertyCaseFinancialScenarioResult = PropertyCaseFinancialAnalysis & {
  scenarioName: string;
};

const INCOMPLETE_MESSAGE = "待補使用者輸入";
const UNAVAILABLE_MESSAGE = "資料不足，暫不可計算";

export function buildPropertyCaseFinancialAnalysis(input: PropertyCaseFinancialInputs): PropertyCaseFinancialAnalysis {
  const listingPrice = positiveMetric(input.listingPrice, "請先輸入有效開價。");
  const userEstimatedValue = optionalPositiveMetric(input.userEstimatedValue, "尚未輸入自估價。");
  const warnings: string[] = [];
  const fundingValue = positiveNumber(input.fundingValue);
  const costs = nonNegativeNumber(input.estimatedBuyerCosts);
  const reserve = nonNegativeNumber(input.renovationReserve);
  const liquidCash = nonNegativeNumber(input.availableLiquidCash);
  const income = nonNegativeNumber(input.monthlyHouseholdIncome);
  const fixedObligations = nonNegativeNumber(input.monthlyFixedObligations);
  const ownershipReserve = nonNegativeNumber(input.monthlyOwnershipReserve);
  const loanYears = positiveNumber(input.loanYears);
  const rate = nonNegativeNumber(input.annualInterestRate);

  if (rate !== null && rate > 100) warnings.push("年利率百分比需介於 0 到 100。");

  const funding = deriveFunding(input.fundingMode, listingPrice.value, fundingValue);
  if (fundingValue !== null && listingPrice.value !== null && fundingValue > listingPrice.value) {
    warnings.push("資金輸入不可大於開價；請調整貸款金額或自備款。");
  }

  const totalCommitment = sumMetric([listingPrice.value, costs, reserve], "需有開價、買方成本與裝修預備金。");
  const cashNeeded = sumMetric([funding.downPayment.value, costs, reserve], "需有自備款、買方成本與裝修預備金。");
  const monthlyPayment = amortizedPaymentMetric(funding.loanAmount.value, loanYears, rate);
  const monthlyBurden = sumMetric([monthlyPayment.value, ownershipReserve], "需有月付與每月持有預備金。");
  const monthlyResidual = subtractMetric(income, [fixedObligations, monthlyBurden.value], "需有月收入、固定支出與月負擔。");
  const postPurchaseCash = subtractMetric(liquidCash, [cashNeeded.value], "需有可動用現金與購屋所需現金。");
  const ltvRatio = ratioMetric(funding.loanAmount.value, listingPrice.value, "需有貸款金額與開價。");
  const userValueGap = differenceMetric(listingPrice.value, userEstimatedValue.value, "需有開價與自估價。");

  return {
    fundingMode: input.fundingMode,
    listingPrice,
    userEstimatedValue,
    loanAmount: funding.loanAmount,
    downPayment: funding.downPayment,
    totalCommitment,
    cashNeeded,
    monthlyPayment,
    monthlyBurden,
    monthlyResidual,
    postPurchaseCash,
    ltvRatio,
    userValueGap,
    warnings,
    isReadyForScenarioComparison: Boolean(
      totalCommitment.status === "available"
      && cashNeeded.status === "available"
      && monthlyPayment.status === "available"
      && monthlyBurden.status === "available",
    ),
  };
}

export function buildPropertyCaseFinancialScenarios(
  base: PropertyCaseFinancialInputs,
  scenarios: PropertyCaseFinancialScenarioInput[],
): PropertyCaseFinancialScenarioResult[] {
  return scenarios.map((scenario, index) => ({
    scenarioName: scenario.scenarioName.trim() || `Scenario ${index + 1}`,
    ...buildPropertyCaseFinancialAnalysis({
      ...base,
      listingPrice: scenario.optionalListingPrice ?? base.listingPrice,
      annualInterestRate: scenario.optionalAnnualInterestRate ?? base.annualInterestRate,
      estimatedBuyerCosts: scenario.optionalEstimatedBuyerCosts ?? base.estimatedBuyerCosts,
      renovationReserve: scenario.optionalRenovationReserve ?? base.renovationReserve,
      monthlyHouseholdIncome: scenario.optionalMonthlyHouseholdIncome ?? base.monthlyHouseholdIncome,
      monthlyFixedObligations: scenario.optionalMonthlyFixedObligations ?? base.monthlyFixedObligations,
      monthlyOwnershipReserve: scenario.optionalMonthlyOwnershipReserve ?? base.monthlyOwnershipReserve,
    }),
  }));
}

function deriveFunding(mode: FundingMode, listingPrice: number | null, fundingValue: number | null) {
  if (listingPrice === null || fundingValue === null) {
    return {
      loanAmount: unavailable("需有開價與資金模式輸入。"),
      downPayment: unavailable("需有開價與資金模式輸入。"),
    };
  }
  if (fundingValue > listingPrice) {
    return {
      loanAmount: unavailable("資金輸入大於開價。"),
      downPayment: unavailable("資金輸入大於開價。"),
    };
  }
  if (mode === "loan_amount") {
    return {
      loanAmount: available(fundingValue),
      downPayment: available(listingPrice - fundingValue),
    };
  }
  return {
    downPayment: available(fundingValue),
    loanAmount: available(listingPrice - fundingValue),
  };
}

function amortizedPaymentMetric(loanAmountWan: number | null, loanYears: number | null, annualRatePercent: number | null): FinancialMetric {
  if (loanAmountWan === null || loanYears === null || annualRatePercent === null) return unavailable("需有貸款金額、年限與利率。");
  if (annualRatePercent > 100) return unavailable("年利率百分比需介於 0 到 100。");
  const principal = loanAmountWan * 10000;
  const months = Math.round(loanYears * 12);
  if (months <= 0) return unavailable("貸款年限需大於 0。");
  if (annualRatePercent === 0) return available(Math.round(principal / months));
  const monthlyRate = annualRatePercent / 100 / 12;
  const payment = principal * monthlyRate * (1 + monthlyRate) ** months / ((1 + monthlyRate) ** months - 1);
  return available(Math.round(payment));
}

function sumMetric(values: Array<number | null>, message: string): FinancialMetric {
  if (values.some((value) => value === null)) return unavailable(message);
  return available(values.reduce<number>((sum, value) => sum + Number(value), 0));
}

function subtractMetric(base: number | null, deductions: Array<number | null>, message: string): FinancialMetric {
  if (base === null || deductions.some((value) => value === null)) return unavailable(message);
  return available(deductions.reduce<number>((result, value) => result - Number(value), base));
}

function ratioMetric(numerator: number | null, denominator: number | null, message: string): FinancialMetric {
  if (numerator === null || denominator === null || denominator <= 0) return unavailable(message);
  return available(numerator / denominator);
}

function differenceMetric(left: number | null, right: number | null, message: string): FinancialMetric {
  if (left === null || right === null) return unavailable(message);
  return available(left - right);
}

function positiveMetric(value: number | null, message: string): FinancialMetric {
  const number = positiveNumber(value);
  return number === null ? unavailable(message) : available(number);
}

function optionalPositiveMetric(value: number | null, message: string): FinancialMetric {
  if (value === null) return { status: "incomplete", value: null, message };
  return positiveMetric(value, message);
}

function positiveNumber(value: number | null): number | null {
  return typeof value === "number" && Number.isFinite(value) && value > 0 ? value : null;
}

function nonNegativeNumber(value: number | null): number | null {
  return typeof value === "number" && Number.isFinite(value) && value >= 0 ? value : null;
}

function available(value: number): FinancialMetric {
  return { status: "available", value, message: "available" };
}

function unavailable(message = UNAVAILABLE_MESSAGE): FinancialMetric {
  return { status: "unavailable", value: null, message: message || INCOMPLETE_MESSAGE };
}
