#!/usr/bin/env python
# -*- coding:utf-8 -*-

__author__ = 'homeway'
__copyright__ = 'Copyright © 2020/6/2, homeway'

import copy
import torch
import torch.nn.functional as F
from model.vertical.party import Party

class Client():
    def __init__(self, uid, conf, data_loader, party, debug=False):
        self.uid = uid
        self.conf = conf
        self.party = party
        self.data_point = -1
        self.data_loader = data_loader
        self.global_params = None
        self.public_key = None
        self.debug = debug
        self.init()

    def init(self):
        self.model = Party(self.party.num_features, self.party.num_output).to(self.conf.device)
        print("-> party={} w={}".format(vars(self.party), self.model.w.shape))

    def load_batch(self, point):
        x, y = list(self.data_loader)[point]
        x, y = x.to(self.conf.device), y.to(self.conf.device)
        return x, y

    def start_round(self, parameters, mask=None, public_key=None):
        self.global_params = copy.deepcopy(parameters)
        self.model.copy_params(self.global_params)

        # TODO: use mask to load batch data
        self.data_point += 1
        self.data_point = self.data_point % len(self.data_loader)
        self.x, self.y = self.load_batch(self.data_point)
        if public_key is not None:
            self.public_key = public_key

    def stop_round(self):
        pass

    def grad_step1(self):
        """exec by A"""
        u_prime = self.model.grad_step1(self.x, self.y)
        return u_prime

    def grad_step2(self, u_prime):
        """exec by B"""
        w, z = self.model.grad_step2(self.x, u_prime)
        return w, z

    def grad_step3(self, w, z):
        """exec by A"""
        z_prime = self.model.grad_step3(self.x, w)
        n = 1.0 / self.conf.batch_size
        return n * z_prime.t(), n * z.t()

    def loss_step1(self):
        """exec by A"""
        u, u_prime = self.model.loss_step1(self.x, self.y)
        return u, u_prime

    def loss_step2(self, u, u_prime):
        """exec by B"""
        v, w = self.model.loss_step2(self.x, u, u_prime)
        return v, w

    def loss_step3(self, u, v, w):
        """exec by A"""
        uv = self.model.loss_step3(self.y, u, v)
        loss = torch.log(torch.tensor([2.0]).to(self.conf.device) + ((w + uv) / self.y.shape[0]).view(-1))
        return loss

    def forward(self, parameters=None):
        if parameters is not None:
            self.global_params = copy.deepcopy(parameters)
            self.model.copy_params(self.global_params)
        return self.model(self.x)

    def batch_evaluation(self, logists, step=0, result={}):
        label = copy.deepcopy(self.y)
        idx = torch.where(label == -1)[0]
        label[idx] = 0

        pred = logists >= 0.5
        truth = label >= 0.5
        acc = 100.0 * pred.eq(truth).sum() / label.shape[0]
        loss = F.binary_cross_entropy(logists, label.float(), reduction="mean")

        result["acc"].append(float(acc))
        result["loss"].append(float(loss))
        result["step"].append(step)
        print(f"-> logist.shape={logists.shape} label.shape={label.shape}\n-> logist={logists[:10].data}\n-> pred={pred.view(-1)[:10]}\n-> y={label.view(-1)[:10]}")
        print(f"-> step={step} train_loss={loss} train_acc={acc}%\n")


































