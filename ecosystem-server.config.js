module.exports = {
  apps: [
    {
      name: 'appservice-server',
      script: 'scripts/run_appservice_server.py',
      cwd: '.',  // Use relative path
      env_file: '.env',
      interpreter: 'python3',  // Use system python or update to your server's python path
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      error_file: 'logs/appservice-error.log',
      out_file: 'logs/appservice-out.log'
    },
    {
      name: 'chat-server',
      script: 'scripts/run_chat_server.py',
      cwd: '.',  // Use relative path
      env_file: '.env',
      interpreter: 'python3',  // Use system python or update to your server's python path
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      error_file: 'logs/chat-error.log',
      out_file: 'logs/chat-out.log'
    },
    {
      name: 'analyzer-server',
      script: 'scripts/run_analyzer_server.py',
      cwd: '.',  // Use relative path
      env_file: '.env',
      interpreter: 'python3',  // Use system python or update to your server's python path
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      error_file: 'logs/analyzer-error.log',
      out_file: 'logs/analyzer-out.log'
    },
    {
      name: 'audio-processor-server',
      script: 'scripts/run_audio_processor_server.py',
      cwd: '.',  // Use relative path
      env_file: '.env.audio_processor',
      interpreter: 'python3',  // Use system python or update to your server's python path
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      error_file: 'logs/audio-processor-error.log',
      out_file: 'logs/audio-processor-out.log'
    }
  ],

  // PM2 deployment configuration for server
  deploy: {
    production: {
      user: 'ubuntu',  // Update to your server user
      host: 'your-server-ip',  // Update to your server IP
      ref: 'origin/main',
      repo: 'git@github.com:Nirva-AI/nirva_service.git',  // Updated repo URL
      path: '/home/ubuntu/nirva_service',  // Update to your server path
      'post-deploy': 'pip install -r requirements.txt && pm2 reload ecosystem-server.config.js --env production'
    }
  }
};
