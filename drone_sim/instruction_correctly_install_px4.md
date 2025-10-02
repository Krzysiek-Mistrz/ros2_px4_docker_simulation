! KONIECZNIE INSTALUJEMY STABILNA WERSJE Z REPO

sudo apt update && sudo apt upgrade -y
sudo apt install -y git wget
git clone --recursive -b v1.16.0 https://github.com/PX4/PX4-Autopilot.git ~/PX4-Autopilot
cd ~/PX4-Autopilot
bash ./Tools/setup/ubuntu.sh
make px4_sitl gz_x500