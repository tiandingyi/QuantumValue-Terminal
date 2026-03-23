export const metricCards = [
  {
    label: "P/E Ratio",
    value: "18.5",
    detail: "Normalized trailing multiple",
  },
  {
    label: "ROE",
    value: "22.3%",
    detail: "Median across the last five filings",
  },
  {
    label: "Debt / Equity",
    value: "0.45",
    detail: "Capital structure still conservative",
  },
  {
    label: "Market Cap",
    value: "$2.8T",
    detail: "Delayed quote for workspace preview",
  },
  {
    label: "Dividend Yield",
    value: "1.2%",
    detail: "Forward indication from the last annual report",
  },
  {
    label: "Beta",
    value: "1.05",
    detail: "5-year monthly regression",
  },
] as const;

export const matrixRows = [
  { year: "2023", revenue: "394.3B", netIncome: "97.0B", eps: "6.13", assets: "352.7B", liabilities: "290.4B" },
  { year: "2022", revenue: "394.3B", netIncome: "99.8B", eps: "6.11", assets: "352.7B", liabilities: "302.0B" },
  { year: "2021", revenue: "365.8B", netIncome: "94.7B", eps: "5.61", assets: "351.0B", liabilities: "287.9B" },
  { year: "2020", revenue: "274.5B", netIncome: "57.4B", eps: "3.28", assets: "323.9B", liabilities: "258.5B" },
  { year: "2019", revenue: "260.2B", netIncome: "55.3B", eps: "2.97", assets: "338.5B", liabilities: "248.0B" },
] as const;

export const priceSeries = {
  labels: ["2014", "2015", "2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023", "2024"],
  values: [100, 120, 140, 160, 180, 200, 220, 240, 260, 280, 300],
} as const;

export const marketSegments = [
  { label: "US Equity", active: true },
  { label: "HK Equity", active: false },
  { label: "A-Share", active: false },
  { label: "Funds", active: false },
  { label: "Global Indices", active: false },
] as const;
