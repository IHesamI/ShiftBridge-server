export const config = {
  appName: process.env.APP_NAME || "ShiftBridge API",
  debugMode: process.env.DEBUG_MODE === "true",
  databaseUrl: process.env.DATABASE_URL || "sqlite:///./shiftbridge.db",
  secretKey: process.env.SECRET_KEY || "default-secret-key",
  algorithm: "HS256" as const,
  accessTokenExpireMinutes: 60,
  port: Number(process.env.PORT) || 3000,
  host: process.env.HOST || "0.0.0.0",
};
