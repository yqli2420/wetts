# Copyright (c) 2022, Yongqiang Li (yongqiangli@alumni.hust.edu.cn)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse

import numpy as np
from scipy.io import wavfile
import torch

import commons
from models import SynthesizerTrn
import utils


def get_args():
    parser = argparse.ArgumentParser(description='inference')
    parser.add_argument('--checkpoint', required=True, help='checkpoint')
    parser.add_argument('--cfg', required=True, help='config file')
    parser.add_argument('--outdir', required=True, help='ouput directory')
    parser.add_argument('--phone', required=True, help='input phone dict')
    parser.add_argument('--test_file', required=True, help='test file')
    args = parser.parse_args()
    return args


def main():
    args = get_args()
    print(args)
    phone_dict = {}
    with open(args.phone) as p_f:
        for line in p_f:
            phone_id = line.strip().split()
            phone_dict[phone_id[0]] = int(phone_id[1])
    hps = utils.get_hparams_from_file(args.cfg)

    net_g = SynthesizerTrn(
        len(phone_dict) + 1, hps.data.filter_length // 2 + 1,
        hps.train.segment_size // hps.data.hop_length, **hps.model).cuda()
    net_g.eval()
    utils.load_checkpoint(args.checkpoint, net_g, None)

    with open(args.test_file) as fin:
        for line in fin:
            audio_text = line.strip().split("|")
            seq = [phone_dict[symbol] for symbol in audio_text[1].split()]
            if hps.data.add_blank:
                seq = commons.intersperse(seq, 0)
            seq = torch.LongTensor(seq)
            with torch.no_grad():
                x = seq.cuda().unsqueeze(0)
                x_length = torch.LongTensor([seq.size(0)]).cuda()
                audio = net_g.infer(
                    x,
                    x_length,
                    noise_scale=.667,
                    noise_scale_w=0.8,
                    length_scale=1)[0][0, 0].data.cpu().float().numpy()
                audio *= 32767 / max(0.01, np.max(np.abs(audio))) * 0.6
                wavfile.write(args.outdir + "/" + audio_text[0].split("/")[-1],
                              hps.data.sampling_rate, audio.astype(np.int16))


if __name__ == '__main__':
    main()
