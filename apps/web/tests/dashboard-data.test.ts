import assert from "node:assert/strict";
import test from "node:test";

import { metricCards, priceSeries } from "../lib/dashboard-data";

test("dashboard data includes metric cards and a matching price series", () => {
  assert.ok(metricCards.length >= 3);
  assert.equal(priceSeries.labels.length, priceSeries.values.length);
});
