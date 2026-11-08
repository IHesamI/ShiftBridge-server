export const config = {
  appName: process.env.APP_NAME || "ShiftBridge API",
  debugMode: process.env.DEBUG_MODE === "true",
  databaseUrl: process.env.DATABASE_URL || "sqlite:///./shiftbridge.db",
  secretKey: process.env.SECRET_KEY || "default-secret-key",
  algorithm: "HS256" as const,
  accessTokenExpireMinutes: 60,
  port: Number(process.env.PORT) || 3000,
  host: process.env.HOST || "0.0.0.0",
  localLlmBaseUrl: process.env.LOCAL_LLM_BASE_URL || process.env.OPENAI_BASE_URL || "http://172.17.0.1:8084",
  localLlmApiKey: process.env.LOCAL_LLM_API_KEY || process.env.OPENAI_API_KEY || "ollama",
  localLlmModel: process.env.LOCAL_LLM_MODEL || "qwen",
};
