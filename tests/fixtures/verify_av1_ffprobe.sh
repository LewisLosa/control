#!/usr/bin/env bash
set -euo pipefail

fixture_dir="$(mktemp -d)"
trap 'rm -rf "$fixture_dir"' EXIT

make_fixture() {
  local name="$1" format="$2" primaries="$3" transfer="$4"
  ffmpeg -hide_banner -loglevel error -y \
    -f lavfi -i "testsrc2=size=320x180:rate=24" -t 0.5 \
    -vf "format=${format}" -c:v libx265 -pix_fmt "${format}" \
    -x265-params "colorprim=${primaries}:transfer=${transfer}:colormatrix=bt2020nc" \
    -color_primaries "${primaries}" -color_trc "${transfer}" -colorspace bt2020nc \
    "${fixture_dir}/${name}.mp4"
}

ffmpeg -hide_banner -loglevel error -y \
  -f lavfi -i testsrc2=size=320x180:rate=24 -t 0.5 \
  -c:v libx264 -pix_fmt yuv420p -color_primaries bt709 -color_trc bt709 -colorspace bt709 \
  "${fixture_dir}/sdr-8bit.mp4"
make_fixture sdr-10bit yuv420p10le bt709 bt709
make_fixture hdr-pq yuv420p10le bt2020 smpte2084
make_fixture hdr-hlg yuv420p10le bt2020 arib-std-b67

for fixture in "${fixture_dir}"/*.mp4; do
  probe_output=$(ffprobe -v error -select_streams v:0 \
    -show_entries stream=pix_fmt,bits_per_raw_sample,color_primaries,color_transfer,color_space \
    -of default=noprint_wrappers=1 "$fixture")
  printf '%s\n%s\n' "$(basename "$fixture")" "$probe_output"
  case "$(basename "$fixture")" in
    sdr-8bit.mp4) grep -q 'pix_fmt=yuv420p' <<<"$probe_output" ;;
    sdr-10bit.mp4) grep -q 'pix_fmt=yuv420p10le' <<<"$probe_output"; grep -q 'color_transfer=bt709' <<<"$probe_output" ;;
    hdr-pq.mp4) grep -q 'pix_fmt=yuv420p10le' <<<"$probe_output"; grep -q 'color_transfer=smpte2084' <<<"$probe_output" ;;
    hdr-hlg.mp4) grep -q 'pix_fmt=yuv420p10le' <<<"$probe_output"; grep -q 'color_transfer=arib-std-b67' <<<"$probe_output" ;;
  esac
done
