from pathlib import Path
from sys import argv
import subprocess
import json
import srt
# import os
import re
# a = Path(argv[1])
# print(a.absolute())
def remove_names(text):
    return re.sub(r"\（(.*?)\）", "", text)
def tryint(s):
    try:
        return int(s)
    except:
        return s
def alphanum_key(s):
    return [ tryint(c) for c in re.split('([0-9]+)', s.name) ]


class VideoClips:

    INDEX = None

    def __init__(self, videofile, padding=1.5):
        self.videofile = videofile
        self.line_padding = padding
        self.intervals = []
        self.duration = float(json.loads(subprocess.check_output([
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_entries', 'format=duration',
            self.videofile]))['format']['duration'])

    def add_clip(self, start, end):
        if start > self.duration:
            return
        self.intervals.append([
            max(0, start - self.line_padding),
            min(self.duration, end + self.line_padding)
        ])

    def _get_merged_intervals(self):
        self.intervals.sort()
        merged_intervals = [self.intervals[0]]
        for ival in self.intervals:
            if ival[0] <= merged_intervals[-1][1]:
                merged_intervals[-1][1] = max(merged_intervals[-1][1], ival[1])
            else:
                merged_intervals.append(ival)
        return merged_intervals

    def export(self):
        if not self.intervals:
            return

        index = VideoClips.INDEX
        vid_json = json.loads(subprocess.check_output([
            'ffprobe.exe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_streams',
            '-select_streams', 'a',
            self.videofile]))
        all_streams = {s["index"]: s for s in vid_json["streams"]}
        if index not in all_streams:
            index = None
        if index is None:
            if not vid_json.get("streams"):
                raise Exception(f"No audio streams to extract {self.videofile}")
            elif len(vid_json["streams"]) == 1:
                index = vid_json["streams"][0]["index"]
            else:
                print("[id]: Tag Information")
                for s in vid_json["streams"]:
                    tags = 'Unknown'
                    try:
                        tags = str(s['tags'])
                    except:
                        pass
                    print(f"[{s['index']}]:\n{tags}\n")
                index = int(input("Pick the audio stream to extract: "))
        VideoClips.INDEX = index

        tmpoutdir = self.videofile.parent / "_tmp_audio"
        # if not tmpoutdir.is_dir():
        #     os.mkdir(tmpoutdir)
        tmpoutdir.mkdir(exist_ok=True)

        merged_intervals = self._get_merged_intervals()
        for start, end in merged_intervals:
            outfile = f"{self.videofile.stem}-{start},{end}.opus"
            # outfile = f'{os.path.splitext(os.path.basename(self.videofile))[0]}-{start},{end}.opus'
            outfile = tmpoutdir / outfile
            subprocess.check_output([
                'ffmpeg', '-y',
                '-ss', str(start),
                '-to', str(end),
                '-i', self.videofile,
                '-map', f'0:{index}',
                outfile])

    @classmethod
    def final_export(cls, dirname):
        tmpoutdir = dirname/"_tmp_audio"
        outdir = dirname
        # if not os.path.isdir(outdir):
        #     os.mkdir(outdir)

        # if CONFIG['group_mp3s_by'] == 'all':
        #     list_file = os.path.join(tmpoutdir, 'list.txt')
        #     with open(list_file, 'w', encoding='utf-8') as lf:
        #         for filename in sorted([a for a in os.listdir(tmpoutdir) if a.endswith('.opus')], key=alphanum_key):
        #             lf.write(f"file '{tmpoutdir}\\{filename}'\n")
        #     outfile = os.path.join(outdir, f"{dirname}.opus")
        #     subprocess.check_output([
        #         os.path.join(get_lib_folder(), 'ffmpeg', 'bin', 'ffmpeg'), '-y',
        #         '-f', 'concat',
        #         '-safe', '0',
        #         '-i', list_file,
        #         '-c', 'copy',
        #         outfile])

        # elif CONFIG['group_mp3s_by'] == 'episode':
        if True:
            list_file = tmpoutdir / "list.txt"
            episodes = set()
            # all_files = sorted([a for a in os.listdir(tmpoutdir) if a.endswith('.opus')], key=alphanum_key)
            all_files = sorted(list(tmpoutdir.glob("*.opus")), key=alphanum_key)
            for filename in all_files:
                episodes.add('-'.join(filename.name.split('-')[:-1]))
            for ep in episodes:
                with open(list_file, 'w', encoding='utf-8') as lf:
                    for f in all_files:
                        if ep in f.name:
                            lf.write(f"file '{f}'\n")
                outfile = outdir / f'{ep}.opus'
                subprocess.check_output([
                    'ffmpeg', '-y',
                    '-f', 'concat',
                    '-safe', '0',
                    '-i', list_file,
                    '-c', 'copy',
                    outfile])

        else:
            os.rename(tmpoutdir, outdir)
        # shutil.rmtree(tmpoutdir, ignore_errors=True)


def main():
    if len(argv) > 1:
        print(argv[1])
        foldpath = Path(argv[1])
    else:
        raise SyntaxError("Specify a folder")
    if len(argv) > 2:
        create_sub = True
    else:
        create_sub = False
    vids = list(foldpath.glob("*mp4")) + list(foldpath.glob("*mkv"))
    subs = [v.with_suffix(".jp.srt") for v in vids]
    print(vids)
    print(subs)
    for vid, sub in zip(vids, subs):
        v = VideoClips(vid)
        with open(sub, "r", encoding='utf-8') as file:
            subgen = list(srt.parse(file.read()))
        for line in subgen:
            if "♪" in line.content:
                continue
            if not len(remove_names(line.content)):
                continue
            if line.start.total_seconds() > line.end.total_seconds():
                raise ValueError("what the fuck")
            v.add_clip(line.start.total_seconds(), line.end.total_seconds())
        v.export()
    VideoClips.final_export(foldpath)
if __name__ == '__main__':
    main()

