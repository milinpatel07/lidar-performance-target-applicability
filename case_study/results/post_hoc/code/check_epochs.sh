#!/bin/bash
# check_epochs.sh - item C: number of training epochs of the four nuScenes ensemble members. Reads only.
# Run inside the container with inputs mounted at /data/inputs.
R=/data/inputs
O=$R/third_party/OpenPCDet/output/workspace/configs
echo "== NUM_EPOCHS in the training configurations"
grep -n "NUM_EPOCHS" $R/configs/cbgs_pp_multihead_nuscenes_seed*.yaml
for s in 1 2 3 4; do
  echo; echo "== member seed $s"
  L=$R/training_seed${s}_nuscenes.log
  echo "-- $L: last epoch progress line and last 'Train: e/20' line"
  tr '\r' '\n' < $L | grep -a "epochs:" | tail -1
  tr '\r' '\n' < $L | grep -a -o "Train: *[0-9]*/[0-9]*" | sort -u -t/ -k1,1 | tail -2
  echo "-- checkpoint files in $O/cbgs_pp_multihead_nuscenes_seed$s/seed_$s/ckpt"
  ls -l --time-style=+%Y-%m-%dT%H:%M $O/cbgs_pp_multihead_nuscenes_seed$s/seed_$s/ckpt | tail -n +2
  echo "-- checkpoint loaded by inference (logs/nuscenes_inference_seed$s.log)"
  grep -a -o -E "[^ ]*\.pth" $R/logs/nuscenes_inference_seed$s.log | sort -u
done
echo; echo "== epoch stored inside latest_model.pth and checkpoint_epoch_10.pth"
python3 - <<'EOF'
import torch
base = "/data/inputs/third_party/OpenPCDet/output/workspace/configs"
for s in (1, 2, 3, 4):
    for f in ("latest_model.pth", "checkpoint_epoch_10.pth"):
        p = f"{base}/cbgs_pp_multihead_nuscenes_seed{s}/seed_{s}/ckpt/{f}"
        c = torch.load(p, map_location="cpu", weights_only=False)
        print(f"seed {s} {f}: epoch={c.get('epoch')} it={c.get('it')}")
EOF
