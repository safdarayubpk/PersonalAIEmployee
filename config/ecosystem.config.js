module.exports = {
  apps: [
    {
      name: "ai-employee-watcher",
      interpreter: "python3",
      script: "src/file_drop_watcher.py",
      cwd: __dirname + "/..",
      max_restarts: 5,
      restart_delay: 1000,
      autorestart: true,
      watch: false,
      out_file: "/home/safdarayub/Documents/AI_Employee_Vault/Logs/watcher-pm2-out.log",
      error_file: "/home/safdarayub/Documents/AI_Employee_Vault/Logs/watcher-pm2-error.log",
      env: {
        VAULT_PATH: "/home/safdarayub/Documents/AI_Employee_Vault",
        DROP_FOLDER: "/home/safdarayub/Desktop/DropForAI",
      },
    },
  ],
};
