# shellcheck disable=SC2164
args=${@:1}
if [ "$args" = "" ]; then
    args="up -d --build"    
fi
echo $args
cd ./docker
docker compose $args
# sleep 3
# python3 -m webbrowser "http://localhost:7900"
