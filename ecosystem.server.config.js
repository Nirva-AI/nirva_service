module.exports = {
  apps: [
    {
      name: 'appservice-server',
      script: 'scripts/run_appservice_server.py',
      cwd: '/home/ec2-user/nirva_service',
      env_file: '.env',
      interpreter: '/home/ec2-user/miniconda3/envs/nirva/bin/python',
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
      cwd: '/home/ec2-user/nirva_service',
      env_file: '.env',
      interpreter: '/home/ec2-user/miniconda3/envs/nirva/bin/python',
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
      cwd: '/home/ec2-user/nirva_service',
      env_file: '.env',
      interpreter: '/home/ec2-user/miniconda3/envs/nirva/bin/python',
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
      cwd: '/home/ec2-user/nirva_service',
      env_file: '.env.audio_processor',
      interpreter: '/home/ec2-user/miniconda3/envs/nirva/bin/python',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      error_file: 'logs/audio-processor-error.log',
      out_file: 'logs/audio-processor-out.log',
      // Restart on failure with delay
      min_uptime: '10s',
      max_restarts: 10,
      restart_delay: 4000
    }
  ],

  // PM2 deployment configuration
  deploy: {
    production: {
      user: 'ec2-user',
      host: 'YOUR_SERVER_IP',
      key: '/path/to/your/key.pem',
      ref: 'origin/main',
      repo: 'https://github.com/Nirva-AI/nirva_service.git',
      path: '/home/ec2-user/nirva_service_deploy',
      'pre-deploy': 'git pull',
      'post-deploy': 'source ~/miniconda3/bin/activate nirva && pip install -e . && ./scripts/run_migration.sh && pm2 reload ecosystem.server.config.js --env production',
      'pre-setup': 'echo "Starting deployment setup"'
    }
  }
};