import fs from "node:fs/promises";
import vm from "node:vm";
import assert from "node:assert/strict";
import ts from "typescript";
const source = await fs.readFile(
  new URL("../src/lib/billing.ts", import.meta.url),
  "utf8",
);
const js = ts.transpileModule(source, {
  compilerOptions: {
    module: ts.ModuleKind.ESNext,
    target: ts.ScriptTarget.ES2022,
  },
}).outputText;
const calls = [];
let loginError = false;
const sdk = {
  configure(args) {
    calls.push(["configure", args.appUserID]);
  },
  async logIn(uid) {
    calls.push(["login", uid]);
    if (loginError) throw new Error("offline");
  },
  async logOut() {
    calls.push(["logout"]);
  },
};
const context = vm.createContext({
  process: { env: { EXPO_PUBLIC_REVENUECAT_IOS_KEY: "appl_public_demo" } },
  console,
});
const native = new vm.SyntheticModule(
  ["Platform"],
  function () {
    this.setExport("Platform", { OS: "ios" });
  },
  { context },
);
const constants = new vm.SyntheticModule(
  ["default"],
  function () {
    this.setExport("default", { executionEnvironment: "standalone" });
  },
  { context },
);
const purchases = new vm.SyntheticModule(
  ["default"],
  function () {
    this.setExport("default", sdk);
  },
  { context },
);
for (const m of [native, constants, purchases]) {
  await m.link(() => {});
  await m.evaluate();
}
const module = new vm.SourceTextModule(js, {
  context,
  importModuleDynamically: () => purchases,
});
await module.link((name) => (name === "react-native" ? native : constants));
await module.evaluate();
const { identifyBilling, billing } = module.namespace;
await identifyBilling(null);
assert.equal(calls.length, 0);
await billing("user-a");
assert.deepEqual(calls, [["configure", "user-a"]]);
await billing("user-a");
assert.equal(calls.length, 1);
await Promise.all([identifyBilling("user-b"), identifyBilling("user-c")]);
assert.deepEqual(calls.slice(-2), [
  ["login", "user-b"],
  ["login", "user-c"],
]);
await identifyBilling(null);
assert.deepEqual(calls.at(-1), ["logout"]);
loginError = true;
await assert.rejects(() => identifyBilling("user-d"), /offline/);
loginError = false;
await billing("user-d");
assert.deepEqual(calls.at(-1), ["login", "user-d"]);
console.log(
  "PASS no anonymous initialization, stable UUID, serialized switches, logout, and retry after identity failure",
);
