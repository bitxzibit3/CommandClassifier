#!/bin/bash
sbatch <<EOT
#!/bin/bash

#SBATCH -J "$1"
#SBATCH -D /s/ls4/users/grartem/RL_robots/CommandClassifier
#SBATCH -o /s/ls4/users/grartem/RL_robots/CommandClassifier/Logs/train_%x_%j.out
#SBATCH -e /s/ls4/users/grartem/RL_robots/CommandClassifier/Logs/train_%x_%j.err
#SBATCH -p hpc5-el7-gpu-3d
#SBATCH -n 1
#SBATCH --gres=gpu:k80:1
#SBATCH --time=72:00:00

export HOME=/s/ls4/users/grartem
#export PATH=\$HOME/anaconda3/envs/rl_robots/bin:\$PATH
export PATH=\$HOME/anaconda3/envs/simptr/bin:\$HOME/RL_robots/CommandClassifier:\$PATH

export LD_LIBRARY_PATH=/s/ls4/sw/cuda/10.1/lib64:/s/ls4/sw/cuda/10.1/nvvm/lib64:\$HOME/installation_dists/cudnn-9.0-linux-x64-v7.1.ga/lib64:
module load gcc/7.3.0

python MultilabelML.py --config_file Configs/CustomML.conf --experiment_name "$1"
EOT