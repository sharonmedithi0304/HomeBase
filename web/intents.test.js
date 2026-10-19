// Run: node web/intents.test.js
const assert = require("assert");
const { parseIntent } = require("./intents.js");
const ctx = { family: ["Maya", "Arjun", "Riya", "Kabir"], today: "2026-10-19" };
const P = (t) => parseIntent(t, ctx);
let n = 0;
const ok = (name, fn) => { fn(); n++; };

ok("briefing", () => assert.strictEqual(P("What's the plan today?").tool, "daily_briefing"));
ok("briefing alexa prefix", () => assert.strictEqual(P("Alexa, what's on today").tool, "daily_briefing"));
ok("briefing tomorrow", () => assert.deepStrictEqual(P("what's the plan tomorrow").args, { day: "2026-10-20" }));
ok("who can pickup", () => {
  const r = P("Who can pick up the kids at 5:30?");
  assert.strictEqual(r.tool, "who_can_pickup");
  assert.strictEqual(r.args.start, "2026-10-19T17:30");
  assert.strictEqual(r.args.end, "2026-10-19T18:15");
});
ok("assign pickup", () => {
  const r = P("Assign the pickup for Kabir from football at 5:30");
  assert.strictEqual(r.tool, "assign_pickup");
  assert.strictEqual(r.args.title, "Pick up Kabir from football");
  assert.strictEqual(r.args.start, "2026-10-19T17:30");
});
ok("pickup bare time", () => assert.strictEqual(P("sort out the pickup at 6").args.start, "2026-10-19T18:00"));
ok("grocery add", () => {
  const r = P("add eggs to the grocery list");
  assert.deepStrictEqual(r, { tool: "grocery_add", args: { item: "Eggs", qty: "1" } });
});
ok("grocery qty dozen", () => assert.deepStrictEqual(P("add a dozen eggs to the shopping list").args, { item: "Eggs", qty: "12" }));
ok("grocery qty number", () => assert.deepStrictEqual(P("put 2 litres of milk on the list").args, { item: "Milk", qty: "2 litres" }));
ok("we need", () => assert.strictEqual(P("we need bananas").args.item, "Bananas"));
ok("grocery added by", () => {
  const r = P("Riya wants me to add chips to the grocery list");
  assert.strictEqual(r.tool, "grocery_add");
  assert.deepStrictEqual(r.args, { item: "Chips", qty: "1", added_by: "Riya" });
});
ok("grocery list", () => assert.strictEqual(P("what's on the grocery list").tool, "grocery_list"));
ok("grocery bought", () => assert.deepStrictEqual(P("check off milk").args, { item: "Milk" }));
ok("complete chore", () => assert.deepStrictEqual(P("I finished the laundry").args, { title: "laundry" }));
ok("complete chore 2", () => assert.strictEqual(P("mark recycling as done").args.title, "recycling"));
ok("complete chore 3", () => assert.strictEqual(P("laundry is done").args.title, "laundry"));
ok("add chore", () => {
  const r = P("add a chore: vacuum the stairs");
  assert.strictEqual(r.tool, "add_chore");
  assert.strictEqual(r.args.title, "Vacuum the stairs");
  assert.strictEqual(r.args.effort, 2);
});
ok("add chore for hard", () => {
  const r = P("add a hard chore clean the garage for Arjun due tomorrow");
  assert.strictEqual(r.args.effort, 4);
  assert.strictEqual(r.args.assignee, "Arjun");
  assert.strictEqual(r.args.due, "2026-10-20");
  assert.strictEqual(r.args.title, "Clean the garage");
});
ok("add event", () => {
  const r = P("schedule school meeting for Arjun at 4pm");
  assert.strictEqual(r.tool, "add_event");
  assert.deepStrictEqual(r.args, { title: "School meeting", member: "Arjun", start: "2026-10-19T16:00", end: "2026-10-19T17:00" });
});
ok("add event possessive", () => {
  const r = P("add Maya's dentist at 3:30 until 4:15");
  assert.strictEqual(r.args.title, "Dentist");
  assert.strictEqual(r.args.end, "2026-10-19T16:15");
});
ok("add event duration", () => {
  const r = P("book piano for Riya at 6 pm for 30 minutes");
  assert.strictEqual(r.args.title, "Piano");
  assert.strictEqual(r.args.end, "2026-10-19T18:30");
});
ok("event needs member", () => assert.ok(P("schedule dentist at 4pm").error));
ok("chore status", () => assert.strictEqual(P("who's turn is it to do chores").tool, "chore_status"));
ok("reset", () => assert.strictEqual(P("reset").special, "reset"));
ok("demo", () => assert.strictEqual(P("load the demo family").tool, "load_demo_family"));
ok("help", () => assert.ok(P("tell me a joke").help));
ok("empty", () => assert.ok(P("   ").help));
console.log(`${n} intent tests passed`);
