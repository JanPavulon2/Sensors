# Installing the backend as a systemd service

The unit file already points at this repo's real location on `karowa-rpi5`
(`/home/aruszku/projects/Sensors`, venv at `.diunaenv`) and runs as root,
since `rpi_ws281x` needs raw `/dev/mem` access for DMA-driven WS281x output -
group membership (`gpio`/`spi`/`i2c`) doesn't cover that. Adjust the paths in
`diuna-backend.service` first if the checkout ever moves.

**Important:** run every command below from a plain SSH session, not VS
Code's integrated terminal - Remote-SSH sets the `no_new_privs` flag on every
process it spawns (including terminal subprocesses), which permanently
blocks `sudo` for that whole session and everything under it. A fresh
`ssh aruszku@karowa-rpi5` connection from a normal terminal app doesn't have
this restriction.

1. Copy the unit file:
   `sudo cp deploy/diuna-backend.service /etc/systemd/system/`
2. The shared secret lives in `deploy/diuna-backend.env`, which the unit file
   pulls in via `EnvironmentFile=` and which is gitignored - the same split as
   `firmware/firmware/include/secrets.h` vs `secrets.h.example`, so the real
   value never reaches git history. That file already exists on this Pi with a
   value matching `NODE_SHARED_SECRET` in the flashed firmware, so no action is
   needed. On a fresh checkout, `cp deploy/diuna-backend.env.example
   deploy/diuna-backend.env` and fill it in. To rotate: update both
   `diuna-backend.env` and firmware `secrets.h`, then reflash every node.
3. Enable and start:
   `sudo systemctl daemon-reload && sudo systemctl enable --now diuna-backend`
4. Check status/logs:
   `systemctl status diuna-backend` / `journalctl -u diuna-backend -f`
