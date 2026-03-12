// PM2 configuration for cloud agent (Platinum tier)
// 4 services on E2.1.Micro (1 OCPU, 1GB RAM) — ADR-0014
//
// NOTE: PM2 v6 has a bug where the `interpreter` field causes Python to
// parse PM2's ProcessContainerForkBun.js. Workaround: use python3 as
// `script` and the .py file as `args`.
//
// Install: pm2 start config/ecosystem.cloud.config.js
// Auto-start: pm2 startup systemd -u ubuntu --hp /home/ubuntu && pm2 save
// Monitor: pm2 list | pm2 monit | pm2 logs

module.exports = {
  apps: [
    {
      name: "cloud-git-sync",
      script: "/home/ubuntu/fte-env/bin/python3",
      args: "src/git_sync.py",
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
      script: "/home/ubuntu/fte-env/bin/python3",
      args: ".claude/skills/gmail-watcher/scripts/gmail_poll.py --minutes 30 --interval 120",
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
      script: "/home/ubuntu/fte-env/bin/python3",
      args: ".claude/skills/daily-scheduler/scripts/scheduler_daemon.py",
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
      script: "/home/ubuntu/fte-env/bin/python3",
      args: ".claude/skills/central-orchestrator/scripts/orchestrator.py --batch-size 5",
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
