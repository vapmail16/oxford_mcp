// ══════════════════════════════════════════════════════════════
// MCP DUNGEON EXPLORER — server.js
// Shows how an AI agent discovers and calls MCP tools at runtime
// ══════════════════════════════════════════════════════════════
const fs = require("fs");
const path = require("path");

const ENV_PATH = path.join(__dirname, ".env");
const dotenvResult = require("dotenv").config({ path: ENV_PATH });

const express = require("express");
const http = require("http");
const WebSocket = require("ws");

/** @type {typeof import("@anthropic-ai/sdk").default | null} */
let Anthropic;
try {
  Anthropic = require("@anthropic-ai/sdk");
} catch (e) {
  Anthropic = null;
}

/** @type {typeof import("openai").default | null} */
let OpenAI;
try {
  OpenAI = require("openai");
} catch (e) {
  OpenAI = null;
}

const ANTHROPIC_MODEL =
  process.env.ANTHROPIC_MODEL || "claude-haiku-4-5-20251001";
const OPENAI_MODEL = process.env.OPENAI_MODEL || "gpt-4o-mini";

const app    = express();
const server = http.createServer(app);
const wss    = new WebSocket.Server({ server });

app.use(express.static(path.join(__dirname, "public")));

// ──────────────────────────────────────────────────────────────
// DUNGEON MAP  (4×4 grid, col,row)
// Victory: pick up ancient_key at (3,1) → reach exit at (3,3)
// ──────────────────────────────────────────────────────────────
const DUNGEON = {
  cols: 4, rows: 4,
  rooms: {
    "0,0":{ name:"Entrance Hall",     desc:"Crumbling stone archway. A torch flickers on the wall.",      enemies:[],                         items:[],                          exits:["east","south"] },
    "1,0":{ name:"Dusty Corridor",    desc:"Long passage. Faded battle-maps scratched into the stone.",   enemies:[],                         items:[{name:"health_potion"}],    exits:["west","east","south"] },
    "2,0":{ name:"Guard Room",        desc:"A crude weapon rack. Something growls from the shadows.",      enemies:[{name:"goblin",hp:30,max:30}], items:[{name:"short_sword"}],  exits:["west","east"] },
    "3,0":{ name:"Dead End",          desc:"Piles of bones and rubble. The only exit is south.",           enemies:[],                         items:[],                          exits:["west","south"] },
    "0,1":{ name:"Flooded Chamber",   desc:"Ankle-deep water. Ice cold. Light filters from above.",        enemies:[],                         items:[],                          exits:["north","east","south"] },
    "1,1":{ name:"Storage Room",      desc:"Broken crates everywhere. Rats scurry in the corners.",        enemies:[],                         items:[],                          exits:["west","east","north","south"] },
    "2,1":{ name:"Crossroads",        desc:"Four passages branch out. You hear distant growling.",          enemies:[],                         items:[],                          exits:["west","east","north","south"] },
    "3,1":{ name:"Key Chamber",       desc:"A stone pedestal at the centre. An ancient key rests on it.",  enemies:[],                         items:[{name:"ancient_key"}],      exits:["west","south","north"] },
    "0,2":{ name:"Fungal Grotto",     desc:"Glowing blue mushrooms light the room. A goblin hisses at you.",enemies:[{name:"goblin",hp:30,max:30}], items:[{name:"health_potion"}], exits:["north","east","south"] },
    "1,2":{ name:"Shrine Room",       desc:"Strange symbols carved on every surface. Silent.",              enemies:[],                         items:[],                          exits:["west","east","north","south"] },
    "2,2":{ name:"Long Hall",         desc:"Empty corridor. Footprints in the dust suggest recent passage.",enemies:[],                         items:[],                          exits:["west","east","north","south"] },
    "3,2":{ name:"Armory",            desc:"Empty weapon racks. An iron shield sits on the floor.",         enemies:[],                         items:[{name:"iron_shield"}],      exits:["west","south","north"] },
    "0,3":{ name:"Crypt",             desc:"Row upon row of sealed stone tombs. Deathly quiet.",            enemies:[],                         items:[],                          exits:["north","east"] },
    "1,3":{ name:"Bone Chamber",      desc:"The air tastes of decay. Remains are piled in the corners.",    enemies:[],                         items:[],                          exits:["west","east","north"] },
    "2,3":{ name:"Final Passage",     desc:"Light seeps under a heavy door to the east. A skeleton guards it.",enemies:[{name:"skeleton",hp:40,max:40}],items:[],               exits:["west","east","north"] },
    "3,3":{ name:"The Iron Door — EXIT",desc:"A massive iron door. Daylight seeps through the cracks. This is the way out.",enemies:[], items:[], exits:["west"], isExit:true },
  }
};

// ──────────────────────────────────────────────────────────────
// GAME STATE  — fresh copy each game
// ──────────────────────────────────────────────────────────────
function freshState() {
  // Deep-clone dungeon rooms so enemies/items reset
  const rooms = JSON.parse(JSON.stringify(DUNGEON.rooms));
  return {
    position: [0,0],
    hp: 100, maxHp: 100,
    attack: 10,
    inventory: [],
    rooms,                   // mutable copy
    steps: 0,
    toolCalls: 0,
    gameOver: false, won: false,
    log: []
  };
}

let STATE = freshState();

// ──────────────────────────────────────────────────────────────
// HELPERS
// ──────────────────────────────────────────────────────────────
function roomKey([col,row]) { return `${col},${row}`; }
function getRoom(state, pos) { return state.rooms[roomKey(pos)]; }
function posStr([c,r]) { return `(${c},${r})`; }

const DIR_DELTA = { north:[0,-1], south:[0,1], east:[1,0], west:[-1,0] };

// ──────────────────────────────────────────────────────────────
// MCP TOOL DEFINITIONS  (same structure as a real MCP server)
// ──────────────────────────────────────────────────────────────
const MCP_TOOLS = [
  {
    name: "move",
    description: "Move one step in a direction. Call this to navigate between rooms. Returns what you see in the new room. Cannot move through walls or into rooms with living enemies blocking the exit.",
    input_schema: {
      type: "object",
      properties: {
        direction: { type:"string", enum:["north","south","east","west"], description:"Direction to move" }
      },
      required: ["direction"]
    }
  },
  {
    name: "attack",
    description: "Attack an enemy in your current room. Call this when there is an enemy in the room. Each attack deals damage. Enemy attacks back. Keep attacking until the enemy is defeated.",
    input_schema: {
      type: "object",
      properties: {
        target: { type:"string", description:"Name of the enemy to attack (e.g. 'goblin', 'skeleton')" }
      },
      required: ["target"]
    }
  },
  {
    name: "pick_up",
    description: "Pick up an item from the current room and add it to your inventory. Call this when you see a useful item in the room.",
    input_schema: {
      type: "object",
      properties: {
        item: { type:"string", description:"Name of the item to pick up (e.g. 'ancient_key', 'health_potion', 'short_sword')" }
      },
      required: ["item"]
    }
  },
  {
    name: "use_item",
    description: "Use an item from your inventory. Use health_potion to restore HP. Equipping a sword increases attack power.",
    input_schema: {
      type: "object",
      properties: {
        item: { type:"string", description:"Name of the item to use (e.g. 'health_potion', 'short_sword', 'ancient_key')" }
      },
      required: ["item"]
    }
  },
  {
    name: "inspect_room",
    description: "Get a detailed description of the current room including all enemies, items, and available exits. Use this when you need more information before deciding what to do.",
    input_schema: { type:"object", properties:{}, required:[] }
  },
  {
    name: "check_inventory",
    description: "List everything in your inventory and your current stats (HP, attack power). Call this to see if you have the key or any useful items.",
    input_schema: { type:"object", properties:{}, required:[] }
  }
];

// ──────────────────────────────────────────────────────────────
// TOOL HANDLERS
// ──────────────────────────────────────────────────────────────
function execTool(state, name, args) {
  state.toolCalls++;
  switch (name) {
    case "move":         return toolMove(state, args.direction);
    case "attack":       return toolAttack(state, args.target);
    case "pick_up":      return toolPickUp(state, args.item);
    case "use_item":     return toolUseItem(state, args.item);
    case "inspect_room": return toolInspect(state);
    case "check_inventory": return toolInventory(state);
    default: return { success:false, message:`Unknown tool: ${name}` };
  }
}

function toolMove(state, dir) {
  const room = getRoom(state, state.position);
  if (!room.exits.includes(dir)) return { success:false, message:`No passage to the ${dir}. Available exits: ${room.exits.join(", ")}.` };

  const [dc,dr] = DIR_DELTA[dir];
  const newPos = [state.position[0]+dc, state.position[1]+dr];
  const newRoom = state.rooms[roomKey(newPos)];
  if (!newRoom) return { success:false, message:"There is only a wall." };

  // Enemies in current room block movement
  if (room.enemies.length > 0) return { success:false, message:`You can't leave — ${room.enemies.map(e=>e.name).join(", ")} block${room.enemies.length===1?"s":""} the way! Defeat them first.` };

  state.position = newPos;
  state.steps++;

  // Win condition
  if (newRoom.isExit) {
    const hasKey = state.inventory.some(i => i.name === "ancient_key");
    if (!hasKey) {
      state.position = [state.position[0]-dc, state.position[1]-dr]; // push back
      return { success:false, message:"The iron door is locked. You need the ancient key to open it." };
    }
    state.gameOver = true; state.won = true;
    return { success:true, message:"🎉 You insert the ancient key into the iron lock. The door swings open. Daylight floods in. YOU ESCAPED THE DUNGEON!", roomName:newRoom.name, won:true };
  }

  const enemies = newRoom.enemies.length > 0 ? ` ⚠️  ENEMY: ${newRoom.enemies.map(e=>`${e.name} (${e.hp}HP)`).join(", ")}` : "";
  const items   = newRoom.items.length   > 0 ? ` 💎 Items: ${newRoom.items.map(i=>i.name).join(", ")}` : "";
  return { success:true, message:`Moved ${dir} → ${newRoom.name}. ${newRoom.desc}${enemies}${items}`, roomName:newRoom.name };
}

function toolAttack(state, target) {
  const room = getRoom(state, state.position);
  const enemy = room.enemies.find(e => e.name.toLowerCase() === target.toLowerCase());
  if (!enemy) return { success:false, message:`No ${target} here. Enemies present: ${room.enemies.map(e=>e.name).join(", ")||"none"}.` };

  const dmg = state.attack + Math.floor(Math.random()*6);
  enemy.hp -= dmg;

  if (enemy.hp <= 0) {
    room.enemies = room.enemies.filter(e => e !== enemy);
    return { success:true, message:`⚔️  You strike the ${enemy.name} for ${dmg} damage. It collapses! The room is clear.`, killed:enemy.name };
  }

  // Enemy counter-attacks
  const eDmg = Math.floor(Math.random()*15) + 5;
  state.hp = Math.max(0, state.hp - eDmg);

  if (state.hp <= 0) {
    state.gameOver = true; state.won = false;
    return { success:false, message:`You hit the ${enemy.name} for ${dmg} damage (${enemy.hp}HP left). It strikes back for ${eDmg}! You have been defeated. 💀`, died:true };
  }

  return { success:true, message:`⚔️  You hit the ${enemy.name} for ${dmg} damage (${enemy.hp}HP left). It strikes back for ${eDmg}! Your HP: ${state.hp}/${state.maxHp}.` };
}

function toolPickUp(state, item) {
  const room = getRoom(state, state.position);
  const idx  = room.items.findIndex(i => i.name.toLowerCase() === item.toLowerCase());
  if (idx === -1) return { success:false, message:`No ${item} in this room. Items here: ${room.items.map(i=>i.name).join(", ")||"none"}.` };

  const picked = room.items.splice(idx, 1)[0];
  state.inventory.push(picked);

  // Auto-equip sword / shield
  if (picked.name === "short_sword")  state.attack = 18;
  if (picked.name === "iron_shield")  state.maxHp  = 120;

  return { success:true, message:`Picked up ${picked.name}. ${picked.name==="ancient_key" ? "🗝️  You now have the key to the exit!" : picked.name==="short_sword" ? "⚔️  Attack power increased to 18!" : picked.name==="iron_shield" ? "🛡️  Max HP increased to 120!" : ""} Inventory: ${state.inventory.map(i=>i.name).join(", ")}.`, item:picked.name };
}

function toolUseItem(state, item) {
  const idx = state.inventory.findIndex(i => i.name.toLowerCase() === item.toLowerCase());
  if (idx === -1) return { success:false, message:`${item} is not in your inventory. Inventory: ${state.inventory.map(i=>i.name).join(", ")||"empty"}.` };

  if (item === "health_potion") {
    state.inventory.splice(idx, 1);
    const healed = Math.min(40, state.maxHp - state.hp);
    state.hp = Math.min(state.maxHp, state.hp + 40);
    return { success:true, message:`Drank health potion. Restored ${healed} HP. HP: ${state.hp}/${state.maxHp}.` };
  }
  return { success:false, message:`${item} is already active or can't be used directly.` };
}

function toolInspect(state) {
  const room = getRoom(state, state.position);
  const pos  = posStr(state.position);
  const enemies = room.enemies.length ? room.enemies.map(e=>`${e.name} (${e.hp}/${e.max}HP)`).join(", ") : "none";
  const items   = room.items.length   ? room.items.map(i=>i.name).join(", ")   : "none";
  return { success:true, message:`📍 Position ${pos} — ${room.name}\n"${room.desc}"\nExits: ${room.exits.join(", ")}\nEnemies: ${enemies}\nItems: ${items}` };
}

function toolInventory(state) {
  const inv = state.inventory.length ? state.inventory.map(i=>i.name).join(", ") : "empty";
  const hasKey = state.inventory.some(i=>i.name==="ancient_key") ? " 🗝️  (you have the exit key!)" : "";
  return { success:true, message:`🎒 Inventory: ${inv}${hasKey}\n❤️  HP: ${state.hp}/${state.maxHp} | ⚔️ Attack: ${state.attack} | Steps: ${state.steps} | Tool calls: ${state.toolCalls}` };
}

// ──────────────────────────────────────────────────────────────
// STATE SNAPSHOT FOR UI
// ──────────────────────────────────────────────────────────────
function uiSnapshot(state, toolName, toolArgs, result, thinking) {
  return {
    type: "update",
    position: state.position,
    hp: state.hp, maxHp: state.maxHp,
    inventory: state.inventory.map(i=>i.name),
    rooms: Object.fromEntries(
      Object.entries(state.rooms).map(([k,r]) => [k, {
        name: r.name,
        enemies: r.enemies.map(e=>e.name),
        items:   r.items.map(i=>i.name),
        exits:   r.exits,
        isExit:  !!r.isExit
      }])
    ),
    toolCall: { name:toolName, args:toolArgs, result:result.message, success:result.success },
    thinking,
    gameOver: state.gameOver,
    won: state.won,
    steps: state.steps,
    toolCalls: state.toolCalls
  };
}

// ──────────────────────────────────────────────────────────────
// SCRIPTED FALLBACK AGENT  (no API key needed)
// Plays intelligently without LLM — good for offline demos
// ──────────────────────────────────────────────────────────────
function scriptedDecision(state) {
  const room = getRoom(state, state.position);
  const [col,row] = state.position;

  // 1. Fight any enemy in room
  if (room.enemies.length > 0) {
    return { tool:"attack", args:{target:room.enemies[0].name}, thinking:`${room.enemies[0].name} blocks my path. I must fight!` };
  }

  // 2. Heal if low HP and has potion
  if (state.hp < 50 && state.inventory.some(i=>i.name==="health_potion")) {
    return { tool:"use_item", args:{item:"health_potion"}, thinking:`HP is critical (${state.hp}/${state.maxHp}). Using health potion.` };
  }

  // 3. Pick up key if present
  if (room.items.some(i=>i.name==="ancient_key")) {
    return { tool:"pick_up", args:{item:"ancient_key"}, thinking:`The ancient key! I need this to escape.` };
  }

  // 4. Pick up useful items
  const useful = room.items.find(i=>["short_sword","health_potion","iron_shield"].includes(i.name));
  if (useful) {
    return { tool:"pick_up", args:{item:useful.name}, thinking:`Found ${useful.name} — picking it up.` };
  }

  // 5. Navigate: toward key if don't have it, toward exit if do
  const hasKey = state.inventory.some(i=>i.name==="ancient_key");
  const [tc, tr] = hasKey ? [3,3] : [3,1];

  // Prefer moves toward target
  const candidates = [];
  if (tc > col && room.exits.includes("east"))  candidates.push({dir:"east",  priority:2});
  if (tc < col && room.exits.includes("west"))  candidates.push({dir:"west",  priority:2});
  if (tr > row && room.exits.includes("south")) candidates.push({dir:"south", priority:2});
  if (tr < row && room.exits.includes("north")) candidates.push({dir:"north", priority:2});

  // Check target room for enemies — avoid if no weapon
  const safeMoves = candidates.filter(m => {
    const [dc,dr] = DIR_DELTA[m.dir];
    const next = state.rooms[`${col+dc},${row+dr}`];
    if (!next) return false;
    if (next.enemies.length > 0 && state.attack <= 10) return false; // avoid if unarmed
    return true;
  });

  const chosen = (safeMoves.length > 0 ? safeMoves : candidates)[0];
  if (chosen) {
    const goal = hasKey ? "the exit" : "the key";
    return { tool:"move", args:{direction:chosen.dir}, thinking:`Navigating toward ${goal}. Moving ${chosen.dir}.` };
  }

  // Fallback: any valid exit
  for (const dir of ["east","south","north","west"]) {
    if (room.exits.includes(dir)) {
      return { tool:"move", args:{direction:dir}, thinking:`Exploring — moving ${dir}.` };
    }
  }

  return { tool:"inspect_room", args:{}, thinking:"Assessing surroundings." };
}

// ──────────────────────────────────────────────────────────────
// ANTHROPIC AGENT  (uses claude-haiku with real tool_use)
// ──────────────────────────────────────────────────────────────
function buildContext(state) {
  const room = getRoom(state, state.position);
  const hasKey = state.inventory.some(i=>i.name==="ancient_key");
  return [
    `CURRENT STATE:`,
    `Position: ${posStr(state.position)} — ${room.name}`,
    `Room: "${room.desc}"`,
    `Exits: ${room.exits.join(", ")}`,
    `Enemies here: ${room.enemies.length ? room.enemies.map(e=>`${e.name} (${e.hp}HP)`).join(", ") : "none"}`,
    `Items here: ${room.items.length ? room.items.map(i=>i.name).join(", ") : "none"}`,
    `Your HP: ${state.hp}/${state.maxHp} | Attack: ${state.attack}`,
    `Inventory: ${state.inventory.length ? state.inventory.map(i=>i.name).join(", ") : "empty"}`,
    `${hasKey ? "✅ You HAVE the ancient_key — head to exit (3,3) via southeast!" : "❌ You need the ancient_key — it is at position (3,1) east of centre."}`,
    `Steps taken: ${state.steps}`,
    ``,
    `What is your next move?`
  ].join("\n");
}

async function anthropicDecision(state, messages, client, model) {
  messages.push({ role:"user", content: buildContext(state) });

  const resp = await client.messages.create({
    model,
    max_tokens: 512,
    system: [
      "You are an AI agent navigating a dungeon. Your ONLY goal is to escape through the locked Iron Door at position (3,3).",
      "To escape: (1) find and pick up the ancient_key at (3,1), (2) navigate to exit at (3,3) and move east.",
      "Grid is 4×4. North=row decreases, South=row increases, East=col increases, West=col decreases.",
      "Fight enemies blocking your path. Collect useful items. Keep your HP above 30.",
      "Make EXACTLY ONE tool call per response. Think in one sentence, then act.",
    ].join(" "),
    tools: MCP_TOOLS,
    messages
  });

  // Extract thinking text and tool call
  const textBlock = resp.content.find(b => b.type === "text");
  const toolBlock = resp.content.find(b => b.type === "tool_use");

  const thinking = textBlock?.text?.slice(0,120) || "Deciding...";

  if (!toolBlock) {
    // No tool call — force a move
    return { tool:"inspect_room", args:{}, thinking, rawContent:resp.content };
  }

  // Add assistant turn to history
  messages.push({ role:"assistant", content: resp.content });

  return { tool:toolBlock.name, args:toolBlock.input, thinking, toolUseId:toolBlock.id, rawContent:resp.content };
}

// ──────────────────────────────────────────────────────────────
// AGENT LOOP
// ──────────────────────────────────────────────────────────────
let loopRunning = false;

async function runAgentLoop(ws, useAI) {
  if (loopRunning) return;
  loopRunning = true;
  STATE = freshState();

  const client =
    useAI && Anthropic && process.env.ANTHROPIC_API_KEY
      ? new Anthropic.default({ apiKey: process.env.ANTHROPIC_API_KEY })
      : null;

  const messages = [];
  const transcript = [];
  let maxSteps = 60;

  // Send initial state
  ws.send(
    JSON.stringify({
      type: "start",
      mode: client
        ? `${ANTHROPIC_MODEL} (Anthropic)`
        : "scripted agent (demo mode)",
      agentModel: client ? ANTHROPIC_MODEL : null,
      ...uiSnapshot(
        STATE,
        null,
        null,
        { message: "Game started. Finding the ancient key...", success: true },
        ""
      ),
    })
  );

  await sleep(800);

  while (!STATE.gameOver && maxSteps-- > 0 && loopRunning) {
    let decision;
    let thinking = "Thinking...";

    try {
      if (client) {
        decision = await anthropicDecision(
          STATE,
          messages,
          client,
          ANTHROPIC_MODEL
        );
        thinking = decision.thinking;
      } else {
        decision = scriptedDecision(STATE);
        thinking = decision.thinking;
        await sleep(300); // extra pause so audience can read
      }
    } catch(err) {
      console.error("Agent error:", err.message);
      decision = scriptedDecision(STATE); // fallback
      thinking = "Deciding...";
    }

    // Show "thinking" state
    ws.send(JSON.stringify({ type:"thinking", text: thinking }));
    await sleep(client ? 200 : 600);

    // Execute the tool
    const result = execTool(STATE, decision.tool, decision.args);
    transcript.push({
      tool: decision.tool,
      args: decision.args,
      result: result.message,
    });

    // If Anthropic, add tool result to conversation
    if (client && decision.toolUseId) {
      messages.push({
        role:"user",
        content:[{ type:"tool_result", tool_use_id:decision.toolUseId, content:result.message }]
      });
    }

    // Push UI update
    const snap = uiSnapshot(STATE, decision.tool, decision.args, result, thinking);
    ws.send(JSON.stringify(snap));

    if (STATE.gameOver) break;
    await sleep(client ? 1200 : 1000);
  }

  if (!STATE.won && !STATE.gameOver) {
    ws.send(
      JSON.stringify({
        type: "timeout",
        message: "Max steps reached — game over.",
      })
    );
  }

  await sendTranscriptReview(transcript, ws);

  loopRunning = false;
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

/**
 * Optional: summarize the session with OpenAI (transcript review).
 * @param {Array<{ tool: string, args: object, result: string }>} transcript
 * @param {import("ws")} ws
 */
async function sendTranscriptReview(transcript, ws) {
  if (!process.env.OPENAI_API_KEY || !OpenAI || transcript.length === 0) return;
  const OpenAIClass = OpenAI.default || OpenAI;
  const client = new OpenAIClass({ apiKey: process.env.OPENAI_API_KEY });
  const text = transcript
    .map(
      (t) =>
        `${t.tool}(${JSON.stringify(t.args)}) → ${String(t.result).slice(0, 400)}`
    )
    .join("\n");
  try {
    const out = await client.chat.completions.create({
      model: OPENAI_MODEL,
      messages: [
        {
          role: "system",
          content:
            "You briefly review MCP-style tool traces from a dungeon crawler. In 2–4 sentences, summarize strategy, risks, and outcome.",
        },
        { role: "user", content: `Tool-call transcript:\n${text}` },
      ],
      max_tokens: 400,
    });
    const summary = out.choices[0]?.message?.content?.trim() || "";
    if (summary && ws.readyState === 1) {
      ws.send(JSON.stringify({ type: "transcript_review", text: summary }));
    }
  } catch (err) {
    console.error("OpenAI transcript review failed:", err.message);
  }
}

// ──────────────────────────────────────────────────────────────
// WEBSOCKET
// ──────────────────────────────────────────────────────────────
wss.on("connection", (ws) => {
  console.log("Client connected");
  ws.send(
    JSON.stringify({
      type: "ready",
      hasApiKey: !!process.env.ANTHROPIC_API_KEY,
      agentModel: process.env.ANTHROPIC_API_KEY ? ANTHROPIC_MODEL : null,
      hasOpenAI: !!process.env.OPENAI_API_KEY,
    })
  );

  ws.on("message", async (raw) => {
    const msg = JSON.parse(raw.toString());
    if (msg.type === "start") {
      loopRunning = false;
      await sleep(100);
      runAgentLoop(ws, msg.useAI !== false).catch(console.error);
    }
    if (msg.type === "stop") {
      loopRunning = false;
    }
    if (msg.type === "reset") {
      loopRunning = false;
      STATE = freshState();
      ws.send(
        JSON.stringify({
          type: "ready",
          hasApiKey: !!process.env.ANTHROPIC_API_KEY,
          agentModel: process.env.ANTHROPIC_API_KEY ? ANTHROPIC_MODEL : null,
          hasOpenAI: !!process.env.OPENAI_API_KEY,
        })
      );
    }
  });

  ws.on("close", () => { loopRunning = false; });
});

// ──────────────────────────────────────────────────────────────
// START
// ──────────────────────────────────────────────────────────────
const PORT = Number(process.env.PORT) || 3333;

server.on("error", (err) => {
  if (err.code === "EADDRINUSE") {
    console.error(`\n  Port ${PORT} is already in use.`);
    console.error(`  Stop the other process (e.g. the previous node server), or run:`);
    console.error(`    PORT=3334 npm start`);
    console.error(`  On macOS you can find the PID with: lsof -i :${PORT}\n`);
    process.exit(1);
  }
  throw err;
});

server.listen(PORT, () => {
  console.log(`\n╔══════════════════════════════════════╗`);
  console.log(`║   MCP Dungeon Explorer               ║`);
  console.log(`║   http://localhost:${PORT}               ║`);
  console.log(`╚══════════════════════════════════════╝`);

  const hasAnthropicKey = !!process.env.ANTHROPIC_API_KEY;
  const envExists = fs.existsSync(ENV_PATH);

  if (!hasAnthropicKey) {
    console.log(`\n  Running in DEMO MODE (no ANTHROPIC_API_KEY in process env)`);
    if (!envExists) {
      console.log(`  No file at: ${ENV_PATH}`);
      console.log(`  Run: cp .env.example .env  then add ANTHROPIC_API_KEY=...\n`);
    } else if (dotenvResult.error) {
      console.log(`  Could not read .env: ${dotenvResult.error.message}\n`);
    } else {
      console.log(`  .env exists but ANTHROPIC_API_KEY is empty or missing.`);
      console.log(`  Open .env and set: ANTHROPIC_API_KEY=sk-ant-...\n`);
    }
  } else {
    console.log(`\n  Anthropic agent active ✓  model: ${ANTHROPIC_MODEL}\n`);
  }
  if (process.env.OPENAI_API_KEY) {
    console.log(`  OpenAI transcript review ✓  model: ${OPENAI_MODEL}\n`);
  }
});
