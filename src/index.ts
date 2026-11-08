import express, { Request, Response, NextFunction } from "express";
import cors from "cors";
import jwt from "jsonwebtoken";
import bcrypt from "bcryptjs";
import { config } from "./config.js";

const app = express();
app.use(cors());
app.use(express.json());

// In-Memory Data Models synced with Seed Data
interface User {
  id: number;
  email: string;
  passwordHash: string;
  fullName: string;
  isActive: boolean;
  createdAt: string;
}

interface Project {
  id: number;
  managerId: number;
  title: string;
  createdAt: string;
  workerIds: number[];
}

interface Shift {
  id: number;
  projectId: number;
  ownerId: number;
  startDate: string;
  length: number;
  createdAt: string;
}

// Pre-seeded Database matching seed.py
const defaultPasswordHash = bcrypt.hashSync("password123", 10);

const users: User[] = [
  {
    id: 1,
    email: "manager@shiftbridge.com",
    passwordHash: defaultPasswordHash,
    fullName: "Sarah Connor (Project Manager)",
    isActive: true,
    createdAt: new Date().toISOString(),
  },
  { id: 2, email: "worker1@shiftbridge.com", passwordHash: defaultPasswordHash, fullName: "Alex Morgan", isActive: true, createdAt: new Date().toISOString() },
  { id: 3, email: "worker2@shiftbridge.com", passwordHash: defaultPasswordHash, fullName: "Brian Davis", isActive: true, createdAt: new Date().toISOString() },
  { id: 4, email: "worker3@shiftbridge.com", passwordHash: defaultPasswordHash, fullName: "Chloe Bennett", isActive: true, createdAt: new Date().toISOString() },
  { id: 5, email: "worker4@shiftbridge.com", passwordHash: defaultPasswordHash, fullName: "David Miller", isActive: true, createdAt: new Date().toISOString() },
  { id: 6, email: "worker5@shiftbridge.com", passwordHash: defaultPasswordHash, fullName: "Elena Rostova", isActive: true, createdAt: new Date().toISOString() },
  { id: 7, email: "worker6@shiftbridge.com", passwordHash: defaultPasswordHash, fullName: "Felix Vance", isActive: true, createdAt: new Date().toISOString() },
  { id: 8, email: "worker7@shiftbridge.com", passwordHash: defaultPasswordHash, fullName: "Grace Hopper", isActive: true, createdAt: new Date().toISOString() },
  { id: 9, email: "worker8@shiftbridge.com", passwordHash: defaultPasswordHash, fullName: "Hector Santos", isActive: true, createdAt: new Date().toISOString() },
  { id: 10, email: "worker9@shiftbridge.com", passwordHash: defaultPasswordHash, fullName: "Iris Chen", isActive: true, createdAt: new Date().toISOString() },
  { id: 11, email: "worker10@shiftbridge.com", passwordHash: defaultPasswordHash, fullName: "James Wilson", isActive: true, createdAt: new Date().toISOString() },
  { id: 12, email: "worker11@shiftbridge.com", passwordHash: defaultPasswordHash, fullName: "Kavita Patel", isActive: true, createdAt: new Date().toISOString() },
  { id: 13, email: "worker12@shiftbridge.com", passwordHash: defaultPasswordHash, fullName: "Liam O'Connor", isActive: true, createdAt: new Date().toISOString() },
  { id: 14, email: "worker13@shiftbridge.com", passwordHash: defaultPasswordHash, fullName: "Maya Lin", isActive: true, createdAt: new Date().toISOString() },
  { id: 15, email: "worker14@shiftbridge.com", passwordHash: defaultPasswordHash, fullName: "Noah Taylor", isActive: true, createdAt: new Date().toISOString() },
  { id: 16, email: "worker15@shiftbridge.com", passwordHash: defaultPasswordHash, fullName: "Olivia Martinez", isActive: true, createdAt: new Date().toISOString() },
];

const projects: Project[] = [
  {
    id: 1,
    managerId: 1,
    title: "Metropolis Skyline Project",
    createdAt: new Date().toISOString(),
    workerIds: [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16],
  },
];

// Generate 15 shifts for the 15 workers staggered across upcoming days
const shifts: Shift[] = [];
const now = new Date();
for (let i = 0; i < 15; i++) {
  const workerId = i + 2;
  const dayOffset = (i % 5) + 1;
  const startHour = i % 2 === 0 ? 8 : 16;
  const shiftDate = new Date(now.getTime() + dayOffset * 24 * 60 * 60 * 1000);
  shiftDate.setHours(startHour, 0, 0, 0);

  shifts.push({
    id: i + 1,
    projectId: 1,
    ownerId: workerId,
    startDate: shiftDate.toISOString(),
    length: 8,
    createdAt: new Date().toISOString(),
  });
}

// Authentication Middleware
interface AuthenticatedRequest extends Request {
  user?: User;
}

const authenticate = (req: AuthenticatedRequest, res: Response, next: NextFunction): void => {
  const authHeader = req.headers.authorization;
  if (!authHeader || !authHeader.startsWith("Bearer ")) {
    res.status(401).json({ detail: "Could not validate credentials" });
    return;
  }

  const token = authHeader.split(" ")[1];
  try {
    const payload = jwt.verify(token, config.secretKey) as { sub: string };
    const user = users.find((u) => u.email === payload.sub);
    if (!user) {
      res.status(401).json({ detail: "User not found" });
      return;
    }
    req.user = user;
    next();
  } catch {
    res.status(401).json({ detail: "Invalid token" });
  }
};

// Tools definitions
const AVAILABLE_TOOLS = [
  {
    name: "get_other_workers_shifts",
    description: "Fetch shifts of other workers in the project to check coworker availability and prevent conflicts.",
    parameters: {
      type: "object",
      properties: {
        project_id: {
          type: "integer",
          description: "ID of the project. If omitted, checks user's assigned project.",
        },
      },
    },
  },
  {
    name: "get_my_shifts",
    description: "Fetch all scheduled shifts belonging to the current user.",
    parameters: {
      type: "object",
      properties: {
        project_id: {
          type: "integer",
          description: "Optional project ID filter.",
        },
      },
    },
  },
  {
    name: "reschedule_shift",
    description: "Change/reschedule an existing shift of the current user to a new date and time.",
    parameters: {
      type: "object",
      properties: {
        shift_id: {
          type: "integer",
          description: "The ID of the shift to reschedule.",
        },
        new_start_date: {
          type: "string",
          description: "The new start date and time (ISO format or YYYY-MM-DD HH:MM).",
        },
        new_length: {
          type: "integer",
          description: "Optional new duration of the shift in hours.",
        },
      },
      required: ["new_start_date"],
    },
  },
];

// Tool Execution Helpers
function executeTool(name: string, args: Record<string, unknown>, user: User): any {
  if (name === "get_other_workers_shifts") {
    const projectId = typeof args.project_id === "number" ? args.project_id : 1;
    const coworkerShifts = shifts
      .filter((s) => s.projectId === projectId && s.ownerId !== user.id)
      .map((s) => {
        const owner = users.find((u) => u.id === s.ownerId);
        const proj = projects.find((p) => p.id === s.projectId);
        return {
          shift_id: s.id,
          project_id: s.projectId,
          project_title: proj?.title || "Unknown",
          worker_id: s.ownerId,
          worker_name: owner?.fullName || "Unknown",
          worker_email: owner?.email || "",
          start_date: s.startDate,
          length: s.length,
        };
      });

    return { success: true, count: coworkerShifts.length, shifts: coworkerShifts };
  }

  if (name === "get_my_shifts") {
    const userShifts = shifts
      .filter((s) => s.ownerId === user.id)
      .map((s) => {
        const proj = projects.find((p) => p.id === s.projectId);
        return {
          shift_id: s.id,
          project_id: s.projectId,
          project_title: proj?.title || "Unknown",
          start_date: s.startDate,
          length: s.length,
        };
      });

    return { success: true, count: userShifts.length, shifts: userShifts };
  }

  if (name === "reschedule_shift") {
    const shiftId = typeof args.shift_id === "number" ? args.shift_id : shifts.find((s) => s.ownerId === user.id)?.id;
    if (!shiftId) {
      return { success: false, error: "No shift found to reschedule." };
    }

    const shift = shifts.find((s) => s.id === shiftId && s.ownerId === user.id);
    if (!shift) {
      return { success: false, error: `Shift #${shiftId} not found or does not belong to you.` };
    }

    const newStartDateStr = String(args.new_start_date || "");
    const parsedDate = new Date(newStartDateStr);
    if (isNaN(parsedDate.getTime())) {
      return { success: false, error: `Invalid date format: '${newStartDateStr}'.` };
    }

    const oldStart = shift.startDate;
    const oldLength = shift.length;

    shift.startDate = parsedDate.toISOString();
    if (typeof args.new_length === "number" && args.new_length > 0) {
      shift.length = args.new_length;
    }

    const proj = projects.find((p) => p.id === shift.projectId);

    return {
      success: true,
      message: `Successfully rescheduled shift #${shift.id}.`,
      shift: {
        shift_id: shift.id,
        project_id: shift.projectId,
        project_title: proj?.title || "Unknown",
        previous_start_date: oldStart,
        new_start_date: shift.startDate,
        previous_length: oldLength,
        new_length: shift.length,
      },
    };
  }

  return { success: false, error: `Unknown tool: ${name}` };
}

// --- API ROUTES ---

// Health check
app.get("/api/health", (_req, res) => {
  res.json({ status: "healthy", service: "ShiftBridge API", version: "1.0.0" });
});

// Authentication Routes
app.post("/auth/signup", (req, res) => {
  const { email, password, full_name } = req.body;
  if (!email || !password) {
    res.status(400).json({ detail: "Email and password required" });
    return;
  }
  if (users.find((u) => u.email === email)) {
    res.status(400).json({ detail: "Email already registered" });
    return;
  }

  const newUser: User = {
    id: users.length + 1,
    email,
    passwordHash: bcrypt.hashSync(password, 10),
    fullName: full_name || email.split("@")[0],
    isActive: true,
    createdAt: new Date().toISOString(),
  };
  users.push(newUser);

  res.status(201).json({
    id: newUser.id,
    email: newUser.email,
    full_name: newUser.fullName,
    is_active: newUser.isActive,
    created_at: newUser.createdAt,
  });
});

app.post("/auth/login", (req, res) => {
  const { email, password } = req.body;
  const user = users.find((u) => u.email === email);
  if (!user || !bcrypt.compareSync(password, user.passwordHash)) {
    res.status(401).json({ detail: "Incorrect email or password" });
    return;
  }

  const token = jwt.sign({ sub: user.email }, config.secretKey, { expiresIn: "1h" });
  res.json({ access_token: token, token_type: "bearer" });
});

app.get("/auth/me", authenticate, (req: AuthenticatedRequest, res: Response) => {
  const user = req.user!;
  res.json({
    id: user.id,
    email: user.email,
    full_name: user.fullName,
    is_active: user.isActive,
    created_at: user.createdAt,
  });
});

// Shifts Routes
app.get("/shifts/my-shifts", authenticate, (req: AuthenticatedRequest, res: Response) => {
  const result = executeTool("get_my_shifts", {}, req.user!);
  res.json(result);
});

app.get("/shifts/project/:projectId/workers", authenticate, (req: AuthenticatedRequest, res: Response) => {
  const projectId = parseInt(req.params.projectId, 10);
  const result = executeTool("get_other_workers_shifts", { project_id: projectId }, req.user!);
  res.json(result);
});

app.patch("/shifts/:shiftId/reschedule", authenticate, (req: AuthenticatedRequest, res: Response) => {
  const shiftId = parseInt(req.params.shiftId, 10);
  const { new_start_date, new_length } = req.body;
  const result = executeTool("reschedule_shift", { shift_id: shiftId, new_start_date, new_length }, req.user!);
  if (!result.success) {
    res.status(400).json({ detail: result.error });
    return;
  }
  res.json(result);
});

// Tools Routes
app.get("/chat/tools", authenticate, (_req, res) => {
  res.json({ tools: AVAILABLE_TOOLS });
});

app.post("/chat/tools/execute", authenticate, (req: AuthenticatedRequest, res: Response) => {
  const { tool_name, arguments: args } = req.body;
  const result = executeTool(tool_name, args || {}, req.user!);
  res.json({ success: result.success, result });
});

// AI Chat Route with Local LLM (OpenAI API Compatible) & Fallback
app.post("/chat", authenticate, async (req: AuthenticatedRequest, res: Response) => {
  const user = req.user!;
  const message = String(req.body.message || "").trim();
  const lowerMsg = message.toLowerCase();

  const toolsUsed: Array<{ tool: string; arguments: Record<string, unknown>; result: unknown }> = [];
  let updatedShiftData: unknown = null;
  let reply = "";

  // Attempt to call Local LLM via OpenAI API (timeout with fast fallback)
  let calledLocalLlm = false;
  try {
    const openaiUrl = `${config.localLlmBaseUrl.replace(/\/+$/, "")}/chat/completions`;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 2500);

    const openAiReq = {
      model: config.localLlmModel,
      messages: [
        {
          role: "system",
          content: `You are ShiftBridge Assistant. User: ${user.fullName} (ID: ${user.id}). Tools available: get_other_workers_shifts, get_my_shifts, reschedule_shift.`,
        },
        { role: "user", content: message },
      ],
      tools: AVAILABLE_TOOLS.map((t) => ({ type: "function", function: t })),
      tool_choice: "auto",
    };

    const llmResp = await fetch(openaiUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${config.localLlmApiKey}`,
      },
      body: JSON.stringify(openAiReq),
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (llmResp.ok) {
      const data = (await llmResp.json()) as any;
      const choice = data.choices?.[0];
      if (choice?.message?.tool_calls) {
        for (const tc of choice.message.tool_calls) {
          const fnName = tc.function.name;
          const fnArgs = JSON.parse(tc.function.arguments || "{}");
          const toolResult = executeTool(fnName, fnArgs, user);
          toolsUsed.push({ tool: fnName, arguments: fnArgs, result: toolResult });
          if (fnName === "reschedule_shift" && toolResult.success) {
            updatedShiftData = toolResult.shift;
          }
        }
        reply = choice.message.content || "I have executed the requested actions for your shift.";
        calledLocalLlm = true;
      } else if (choice?.message?.content) {
        reply = choice.message.content;
        calledLocalLlm = true;
      }
    }
  } catch {
    // Local LLM server offline or unreachable; fall through to intelligent local tool engine
  }

  // Resilient Local Engine Fallback
  if (!calledLocalLlm) {
    const isOtherWorkers = /other\s*worker|coworker|colleague|who\s*is\s*working|other\s*shift/i.test(lowerMsg);
    const isReschedule = /reschedule|change\s*shift|move\s*shift|postpone|switch\s*shift/i.test(lowerMsg);
    const isMyShifts = /my\s*shift|my\s*schedule|when\s*do\s*i\s*work/i.test(lowerMsg);

    // Extract shift ID
    const shiftMatch = lowerMsg.match(/shift\s*(?:id|#)?\s*(\d+)/i);
    const shiftId = shiftMatch ? parseInt(shiftMatch[1], 10) : undefined;

    // Extract length/hours
    const lengthMatch = lowerMsg.match(/(?:for|length|duration)\s*(\d+)\s*(?:hours|hrs|hr)?/i) || lowerMsg.match(/(\d+)\s*(?:hours|hrs)/i);
    const length = lengthMatch ? parseInt(lengthMatch[1], 10) : undefined;

    // Extract date
    let dateStr: string | null = null;
    const isoMatch = message.match(/(\d{4}[-/]\d{1,2}[-/]\d{1,2}(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?)/);
    if (isoMatch) {
      dateStr = isoMatch[1];
    } else if (lowerMsg.includes("tomorrow")) {
      const tomorrow = new Date(Date.now() + 24 * 60 * 60 * 1000);
      tomorrow.setHours(9, 0, 0, 0);
      dateStr = tomorrow.toISOString();
    }

    if (isOtherWorkers) {
      const toolRes = executeTool("get_other_workers_shifts", { project_id: 1 }, user);
      toolsUsed.push({ tool: "get_other_workers_shifts", arguments: { project_id: 1 }, result: toolRes });
      const coworkerShifts = toolRes.shifts || [];
      reply = `Here are the scheduled shifts for other workers on the Metropolis Skyline Project (${coworkerShifts.length} found):\n` +
        coworkerShifts
          .slice(0, 8)
          .map((s: any) => `• ${s.worker_name}: ${s.start_date.replace("T", " ").slice(0, 16)} (${s.length} hrs) [Shift #${s.shift_id}]`)
          .join("\n");
    } else if (isReschedule) {
      if (!dateStr) {
        const myShifts = executeTool("get_my_shifts", {}, user);
        toolsUsed.push({ tool: "get_my_shifts", arguments: {}, result: myShifts });
        reply = `I can help you reschedule your shift. What new date and time would you like?\n\nYour current shift(s):\n` +
          (myShifts.shifts || []).map((s: any) => `• Shift #${s.shift_id} on ${s.start_date.replace("T", " ").slice(0, 16)} (${s.length} hrs)`).join("\n") +
          `\n\nReply with e.g. "Reschedule shift 1 to 2026-11-20 09:00 for 8 hours".`;
      } else {
        const toolRes = executeTool("reschedule_shift", { shift_id: shiftId, new_start_date: dateStr, new_length: length }, user);
        toolsUsed.push({ tool: "reschedule_shift", arguments: { shift_id: shiftId, new_start_date: dateStr, new_length: length }, result: toolRes });
        if (toolRes.success && toolRes.shift) {
          updatedShiftData = toolRes.shift;
          reply = `✅ Shift #${toolRes.shift.shift_id} has been successfully rescheduled to ${toolRes.shift.new_start_date.replace("T", " ").slice(0, 16)} (${toolRes.shift.new_length} hours)!`;
        } else {
          reply = `❌ Could not reschedule shift: ${toolRes.error || "Failed to reschedule"}`;
        }
      }
    } else if (isMyShifts) {
      const toolRes = executeTool("get_my_shifts", {}, user);
      toolsUsed.push({ tool: "get_my_shifts", arguments: {}, result: toolRes });
      const userShifts = toolRes.shifts || [];
      reply = `You have ${userShifts.length} scheduled shift(s):\n` +
        userShifts.map((s: any) => `• Shift #${s.shift_id}: ${s.start_date.replace("T", " ").slice(0, 16)} (${s.length} hrs)`).join("\n");
    } else {
      reply = `Hello ${user.fullName}! I am your AI Shift Assistant.\n\n` +
        `You can ask me to:\n` +
        `1. "Show other workers' shifts for project 1"\n` +
        `2. "What are my upcoming shifts?"\n` +
        `3. "Reschedule shift to 2026-11-20 09:00 for 8 hours"`;
    }
  }

  res.json({
    reply,
    tools_used: toolsUsed,
    updated_shift: updatedShiftData,
  });
});

// Interactive Web UI Dashboard
app.get("/", (_req, res) => {
  res.send(`<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ShiftBridge - AI Shift Scheduling & Management</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <style>
    body { background-color: #0b0f17; color: #f1f5f9; font-family: system-ui, -apple-system, sans-serif; }
    .glass { background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.08); }
    .bubble-ai { background: #1e293b; border-left: 4px solid #38bdf8; }
    .bubble-user { background: #0284c7; }
  </style>
</head>
<body class="min-h-screen flex flex-col">
  <!-- Top Navigation -->
  <header class="border-b border-slate-800 bg-slate-900/80 sticky top-0 z-50 px-6 py-4 flex flex-wrap items-center justify-between gap-4">
    <div class="flex items-center gap-3">
      <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center font-bold text-white shadow-lg shadow-sky-500/20">
        <i class="fa-solid fa-calendar-days text-lg"></i>
      </div>
      <div>
        <h1 class="text-xl font-bold tracking-tight text-white flex items-center gap-2">
          ShiftBridge
          <span class="text-xs font-semibold px-2 py-0.5 rounded-full bg-sky-500/10 text-sky-400 border border-sky-500/20">FastAPI & Express</span>
        </h1>
        <p class="text-xs text-slate-400">AI Shift Scheduling with Local LLM (OpenAI API Compatible)</p>
      </div>
    </div>

    <!-- Active User & Switcher -->
    <div class="flex items-center gap-3">
      <div class="text-right hidden sm:block">
        <div id="currentUserName" class="text-sm font-semibold text-slate-200">Alex Morgan</div>
        <div id="currentUserRole" class="text-xs text-sky-400">Worker (#2) • Metropolis Skyline</div>
      </div>
      <select id="userSelector" class="bg-slate-800 text-slate-200 border border-slate-700 rounded-lg px-3 py-1.5 text-xs focus:ring-2 focus:ring-sky-500 outline-none">
        <option value="manager@shiftbridge.com">Sarah Connor (Manager)</option>
        <option value="worker1@shiftbridge.com" selected>Alex Morgan (Worker 1)</option>
        <option value="worker2@shiftbridge.com">Brian Davis (Worker 2)</option>
        <option value="worker3@shiftbridge.com">Chloe Bennett (Worker 3)</option>
        <option value="worker4@shiftbridge.com">David Miller (Worker 4)</option>
        <option value="worker5@shiftbridge.com">Elena Rostova (Worker 5)</option>
      </select>
    </div>
  </header>

  <!-- Main Container -->
  <main class="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 grid grid-cols-1 lg:grid-cols-12 gap-6">
    <!-- Left Column: AI Assistant Chat -->
    <div class="lg:col-span-7 flex flex-col glass rounded-2xl p-5 shadow-xl h-[700px]">
      <div class="flex items-center justify-between pb-4 border-b border-slate-700/60">
        <div class="flex items-center gap-2.5">
          <div class="w-3 h-3 rounded-full bg-emerald-400 animate-pulse"></div>
          <h2 class="font-bold text-slate-100 flex items-center gap-2">
            Local AI Shift Assistant
            <span class="text-xs text-slate-400 font-normal">(${config.localLlmModel} @ ${config.localLlmBaseUrl})</span>
          </h2>
        </div>
        <button onclick="clearChat()" class="text-xs text-slate-400 hover:text-slate-200 transition">
          <i class="fa-solid fa-trash-can mr-1"></i> Clear
        </button>
      </div>

      <!-- Quick prompts -->
      <div class="py-3 flex flex-wrap gap-2 text-xs border-b border-slate-800/80">
        <button onclick="sendQuick('Show other workers shifts on project 1')" class="bg-slate-800/90 hover:bg-slate-700 text-slate-300 px-3 py-1.5 rounded-lg border border-slate-700/50 transition">
          <i class="fa-solid fa-users text-sky-400 mr-1.5"></i> Coworker Shifts
        </button>
        <button onclick="sendQuick('What are my upcoming shifts?')" class="bg-slate-800/90 hover:bg-slate-700 text-slate-300 px-3 py-1.5 rounded-lg border border-slate-700/50 transition">
          <i class="fa-solid fa-clock text-amber-400 mr-1.5"></i> My Shifts
        </button>
        <button onclick="sendQuick('Reschedule my shift to tomorrow at 09:00 for 8 hours')" class="bg-slate-800/90 hover:bg-slate-700 text-slate-300 px-3 py-1.5 rounded-lg border border-slate-700/50 transition">
          <i class="fa-solid fa-arrows-rotate text-emerald-400 mr-1.5"></i> Reschedule to Tomorrow
        </button>
      </div>

      <!-- Messages container -->
      <div id="chatMessages" class="flex-1 overflow-y-auto space-y-4 py-4 pr-1 text-sm">
        <div class="p-4 rounded-xl bubble-ai text-slate-200">
          <div class="flex items-center gap-2 font-semibold text-sky-400 mb-1.5">
            <i class="fa-solid fa-robot"></i> ShiftBridge AI Assistant
          </div>
          <p>Hello! I am your AI Shift Scheduling Assistant. You can chat with me in natural language to:</p>
          <ul class="list-disc list-inside mt-2 space-y-1 text-slate-300 text-xs">
            <li><strong>Inspect coworker shifts:</strong> <em>"Show me other workers' shifts on Skyline Project"</em></li>
            <li><strong>Check your upcoming schedule:</strong> <em>"What shifts do I have?"</em></li>
            <li><strong>Reschedule your shift:</strong> <em>"Reschedule my shift to 2026-11-20 at 09:00"</em></li>
          </ul>
        </div>
      </div>

      <!-- Input box -->
      <form id="chatForm" onsubmit="handleChatSubmit(event)" class="mt-3 flex gap-2">
        <input id="chatInput" type="text" placeholder="Type a message (e.g. 'Reschedule my shift to Friday at 10:00 AM')..."
          class="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500 transition" />
        <button type="submit" id="sendBtn" class="bg-sky-500 hover:bg-sky-400 text-white font-medium px-5 py-2.5 rounded-xl transition shadow-lg shadow-sky-500/20 flex items-center gap-2 text-sm">
          <span>Send</span>
          <i class="fa-solid fa-paper-plane text-xs"></i>
        </button>
      </form>
    </div>

    <!-- Right Column: Projects & Shifts Overview -->
    <div class="lg:col-span-5 flex flex-col gap-6">
      <!-- Project Card -->
      <div class="glass rounded-2xl p-5 shadow-xl">
        <div class="flex items-center justify-between mb-3">
          <span class="text-xs uppercase font-semibold text-sky-400 tracking-wider">Active Project</span>
          <span class="text-xs bg-slate-800 text-slate-300 px-2.5 py-1 rounded-md border border-slate-700">Project #1</span>
        </div>
        <h3 class="text-lg font-bold text-white mb-1">Metropolis Skyline Project</h3>
        <p class="text-xs text-slate-400 mb-3">Managed by Sarah Connor • 15 Assigned Workers</p>
        <div class="flex items-center gap-2 text-xs text-slate-300 bg-slate-800/60 p-3 rounded-xl border border-slate-700/50">
          <i class="fa-solid fa-shield-halved text-sky-400 text-base"></i>
          <div>
            <strong>15 Active Team Members</strong>
            <p class="text-slate-400 text-[11px]">All 15 worker accounts are linked and scheduled.</p>
          </div>
        </div>
      </div>

      <!-- Live Shifts List -->
      <div class="glass rounded-2xl p-5 shadow-xl flex-1 flex flex-col h-[460px]">
        <div class="flex items-center justify-between pb-3 border-b border-slate-700/60 mb-3">
          <h3 class="font-bold text-slate-100 text-sm flex items-center gap-2">
            <i class="fa-solid fa-calendar-check text-sky-400"></i>
            Project Shifts Schedule
          </h3>
          <button onclick="loadShifts()" class="text-xs text-sky-400 hover:text-sky-300">
            <i class="fa-solid fa-rotate-right mr-1"></i> Refresh
          </button>
        </div>

        <div id="shiftsContainer" class="flex-1 overflow-y-auto space-y-2 pr-1 text-xs">
          <!-- Populated by JavaScript -->
          <div class="text-slate-500 text-center py-6">Loading shifts...</div>
        </div>
      </div>
    </div>
  </main>

  <script>
    let authToken = "";
    let currentUserEmail = "worker1@shiftbridge.com";

    // Auto-login on user selector change
    async function loginAs(email) {
      currentUserEmail = email;
      try {
        const res = await fetch("/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: email, password: "password123" })
        });
        const data = await res.json();
        authToken = data.access_token;
        updateUserUI();
        loadShifts();
      } catch (err) {
        console.error("Login failed", err);
      }
    }

    async function updateUserUI() {
      try {
        const res = await fetch("/auth/me", {
          headers: { "Authorization": "Bearer " + authToken }
        });
        const user = await res.json();
        document.getElementById("currentUserName").innerText = user.full_name;
        document.getElementById("currentUserRole").innerText = user.id === 1 ? "Project Manager" : "Worker (#" + user.id + ") • Skyline";
      } catch (err) {
        console.error(err);
      }
    }

    async function loadShifts() {
      const container = document.getElementById("shiftsContainer");
      try {
        const res = await fetch("/shifts/project/1/workers", {
          headers: { "Authorization": "Bearer " + authToken }
        });
        const data = await res.json();
        const shifts = data.shifts || [];

        const myShiftsRes = await fetch("/shifts/my-shifts", {
          headers: { "Authorization": "Bearer " + authToken }
        });
        const myData = await myShiftsRes.json();
        const myShifts = (myData.shifts || []).map(s => ({ ...s, isMe: true, worker_name: "You" }));

        const all = [...myShifts, ...shifts].sort((a,b) => new Date(a.start_date) - new Date(b.start_date));

        if (!all.length) {
          container.innerHTML = '<div class="text-slate-500 text-center py-6">No shifts found.</div>';
          return;
        }

        container.innerHTML = all.map(s => {
          const date = new Date(s.start_date);
          const dateStr = date.toLocaleDateString("en-US", { weekday: 'short', month: 'short', day: 'numeric' }) + " " + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
          const isMine = s.isMe;

          return \`
            <div class="p-3 rounded-xl border \${isMine ? 'bg-sky-500/10 border-sky-500/30' : 'bg-slate-800/40 border-slate-700/40'} flex items-center justify-between gap-2">
              <div>
                <div class="font-semibold \${isMine ? 'text-sky-300' : 'text-slate-200'} flex items-center gap-2">
                  <span>\${s.worker_name}</span>
                  \${isMine ? '<span class="text-[10px] bg-sky-500/20 text-sky-300 px-1.5 py-0.5 rounded">Your Shift</span>' : ''}
                </div>
                <div class="text-[11px] text-slate-400 mt-0.5">
                  <i class="fa-regular fa-clock mr-1 text-slate-500"></i>\${dateStr} (\${s.length} hrs) • Shift #\${s.shift_id}
                </div>
              </div>
              \${isMine ? \`<button onclick="sendQuick('Reschedule my shift #\${s.shift_id} to tomorrow at 09:00')" class="text-[11px] bg-slate-700 hover:bg-slate-600 text-slate-200 px-2 py-1 rounded transition">Reschedule</button>\` : ''}
            </div>
          \`;
        }).join("");
      } catch (err) {
        container.innerHTML = '<div class="text-red-400 text-center py-6">Failed to load shifts.</div>';
      }
    }

    function appendMessage(role, text, toolsUsed) {
      const container = document.getElementById("chatMessages");
      const div = document.createElement("div");
      div.className = role === "user" ? "p-3.5 rounded-xl bubble-user text-white ml-auto max-w-[85%]" : "p-4 rounded-xl bubble-ai text-slate-200 mr-auto max-w-[90%]";
      
      let toolBadge = "";
      if (toolsUsed && toolsUsed.length) {
        toolBadge = '<div class="mb-2 flex flex-wrap gap-1">' + toolsUsed.map(t => \`<span class="text-[10px] bg-sky-500/20 text-sky-300 border border-sky-500/30 px-2 py-0.5 rounded-md font-mono"><i class="fa-solid fa-wrench mr-1"></i>\${t.tool}</span>\`).join("") + '</div>';
      }

      div.innerHTML = (role === "ai" ? '<div class="flex items-center gap-2 font-semibold text-sky-400 text-xs mb-1.5"><i class="fa-solid fa-robot"></i> ShiftBridge AI</div>' : '<div class="text-xs font-semibold text-sky-200 mb-1">You</div>') + toolBadge + '<div class="whitespace-pre-wrap leading-relaxed">' + text + '</div>';

      container.appendChild(div);
      container.scrollTop = container.scrollHeight;
    }

    async function handleChatSubmit(e) {
      if (e) e.preventDefault();
      const input = document.getElementById("chatInput");
      const msg = input.value.trim();
      if (!msg) return;

      input.value = "";
      appendMessage("user", msg);

      const sendBtn = document.getElementById("sendBtn");
      sendBtn.disabled = true;
      sendBtn.innerHTML = '<i class="fa-solid fa-spinner animate-spin"></i>';

      try {
        const res = await fetch("/chat", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + authToken
          },
          body: JSON.stringify({ message: msg })
        });
        const data = await res.json();
        appendMessage("ai", data.reply || "Done.", data.tools_used);
        if (data.updated_shift) {
          loadShifts();
        }
      } catch (err) {
        appendMessage("ai", "Sorry, an error occurred while processing your request.");
      } finally {
        sendBtn.disabled = false;
        sendBtn.innerHTML = '<span>Send</span><i class="fa-solid fa-paper-plane text-xs"></i>';
      }
    }

    function sendQuick(text) {
      document.getElementById("chatInput").value = text;
      handleChatSubmit();
    }

    function clearChat() {
      document.getElementById("chatMessages").innerHTML = "";
    }

    document.getElementById("userSelector").addEventListener("change", (e) => {
      loginAs(e.target.value);
    });

    // Initial Login
    loginAs("worker1@shiftbridge.com");
  </script>
</body>
</html>`);
});

// Start Server
app.listen(config.port, config.host, () => {
  console.log(`🚀 ShiftBridge server running on http://${config.host}:${config.port}`);
  console.log(`🤖 Local LLM Target: ${config.localLlmModel} @ ${config.localLlmBaseUrl}`);
});
