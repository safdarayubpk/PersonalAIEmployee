// PM2 configuration for cloud agent (Platinum tier)
// 4 services on E2.1.Micro (1 OCPU, 1GB RAM) — ADR-0014
// Install: pm2 start config/ecosystem.cloud.config.js
// Auto-start: pm2 startup systemd -u ubuntu --hp /home/ubuntu && pm2 save
// Monitor: pm2 list | pm2 monit | pm2 logs

module.exports = {
  apps: [
    {
      name: "cloud-git-sync",
      interpreter: "/home/ubuntu/fte-env/bin/python3",
      script: "src/git_sync.py",
      cwd: "/home/ubuntu/AI_Employee_Vault",
      max_restarts: 5,
      min_uptime: "60s",
      restart_delay: 5000,
      kill_timeout: 10000,
      autorestart: true,
      max_memory_restart: "150M",
      env: {
        FTE_ROLE: "cloud",
        VAULT_PATH: "/home/ubuntu/AI_Employee_Vault",
        PROJECT_ROOT: "/home/ubuntu/AI_Employee_Vault",
        GIT_SYNC_INTERVAL_SECONDS: "60",
      },
    },
    {
      name: "cloud-gmail-watcher",
      interpreter: "/home/ubuntu/fte-env/bin/python3",
      script: ".claude/skills/gmail-watcher/scripts/gmail_poll.py",
      args: "--minutes 30 --interval 120",
      cwd: "/home/ubuntu/AI_Employee_Vault",
      max_restarts: 5,
      min_uptime: "60s",
      restart_delay: 5000,
      kill_timeout: 10000,
      autorestart: true,
      max_memory_restart: "200M",
      env: {
        FTE_ROLE: "cloud",
        VAULT_PATH: "/home/ubuntu/AI_Employee_Vault",
        PROJECT_ROOT: "/home/ubuntu/AI_Employee_Vault",
        DRY_RUN: "true",
      },
    },
    {
      name: "cloud-scheduler",
      interpreter: "/home/ubuntu/fte-env/bin/python3",
      script: ".claude/skills/daily-scheduler/scripts/scheduler_daemon.py",
      cwd: "/home/ubuntu/AI_Employee_Vault",
      max_restarts: 5,
      min_uptime: "60s",
      restart_delay: 5000,
      kill_timeout: 10000,
      autorestart: true,
      max_memory_restart: "150M",
      env: {
        FTE_ROLE: "cloud",
        VAULT_PATH: "/home/ubuntu/AI_Employee_Vault",
        PROJECT_ROOT: "/home/ubuntu/AI_Employee_Vault",
      },
    },
    {
      name: "cloud-orchestrator",
      interpreter: "/home/ubuntu/fte-env/bin/python3",
      script: ".claude/skills/central-orchestrator/scripts/orchestrator.py",
      args: "--batch-size 5",
      cwd: "/home/ubuntu/AI_Employee_Vault",
      max_restarts: 5,
      min_uptime: "60s",
      restart_delay: 10000,
      kill_timeout: 10000,
      autorestart: true,
      max_memory_restart: "200M",
      cron_restart: "*/5 * * * *",
      env: {
        FTE_ROLE: "cloud",
        VAULT_PATH: "/home/ubuntu/AI_Employee_Vault",
        PROJECT_ROOT: "/home/ubuntu/AI_Employee_Vault",
      },
    },
  ],
};
