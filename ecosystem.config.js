module.exports = {
  apps: [
    {
      name: 'appservice-server',
      script: 'python',
      args: 'scripts/run_appservice_server.py',
      cwd: '/Users/rumiyy/nirva/nirva_service',
      env_file: '.env',
      interpreter: 'python',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G'
    },
    {
      name: 'chat-server',
      script: 'python',
      args: 'scripts/run_chat_server.py',
      cwd: '/Users/rumiyy/nirva/nirva_service',
      env_file: '.env',
      interpreter: 'python',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G'
    },
    {
      name: 'analyzer-server',
      script: 'python',
      args: 'scripts/run_analyzer_server.py',
      cwd: '/Users/rumiyy/nirva/nirva_service',
      env_file: '.env',
      interpreter: 'python',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G'
    },
    {
      name: 'audio-processor-server',
      script: 'python',
      args: 'scripts/run_audio_processor_server.py',
      cwd: '/Users/rumiyy/nirva/nirva_service',
      env_file: '.env.audio_processor',  // Uses separate env file with different AWS credentials
      interpreter: 'python',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      error_file: 'logs/audio-processor-error.log',
      out_file: 'logs/audio-processor-out.log'
    }
  ],

  // PM2 deployment configuration (optional, for future use)
  deploy: {
    production: {
      user: 'node',
      host: 'your-server-ip',
      ref: 'origin/main',
      repo: 'git@github.com:your-repo.git',
      path: '/var/www/nirva_service',
      'post-deploy': 'conda activate nirva && pm2 reload ecosystem.config.js --env production'
    }
  }
};