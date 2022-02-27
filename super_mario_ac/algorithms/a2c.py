#
# File: super_mario_ac/algorithms/a2c.py
# Auth: Oscar Ligthart
# Desc: The A2C algorithm for learning to play Super Mario
#
###################################################

import sys
import torch
import gym
import numpy as np
import torch.nn as nn
import torch.optim as optim
from torch.distributions import Categorical
import torch.nn.functional as F
from torch.autograd import Variable
import matplotlib.pyplot as plt
import pandas as pd


class A2C:
    """
    The A2C algorithm, responsible for training an Actor-Critic model
    in a gym environment
    """
    def __init__(self, model, args):

        # set device
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        # store variables
        self.actor_critic = model
        self.actor_critic.to(self.device)
        self.args = args

        # initialize optimizer
        self.optimizer = optim.Adam(self.actor_critic.parameters(), lr=self.args.lr)

        # initialize hidden states
        self.h_0 = torch.zeros((1, 512), dtype=torch.float).to(self.device)
        self.c_0 = torch.zeros((1, 512), dtype=torch.float).to(self.device)

    def reset(self):
        """
        Method to reset the algorithm in between episodes
        :return:
        """
        # reinitialize hidden states
        self.h_0 = torch.zeros((1, 512), dtype=torch.float).to(self.device)
        self.c_0 = torch.zeros((1, 512), dtype=torch.float).to(self.device)

    def select_action(self, state):
        """
        Method to select an action given a specific game state
        :param state:
        :return:
        """

        state = state.to(self.device)

        # run a forward pass to get an action
        policy, value, self.h_0, self.c_0 = self.actor_critic.forward(state, self.h_0, self.c_0)

        self.h_0 = self.h_0.data
        self.c_0 = self.c_0.data

        # calculate action probabilites, log probabilities and entropy
        prob = F.softmax(policy, dim=1)
        log_prob = F.log_softmax(policy, dim=1)
        entropy = -(policy * log_prob).sum(1, keepdim=True)

        # sample an action
        m = Categorical(prob)
        action = m.sample().item()

        return action, value, log_prob, entropy

    def update(self, final_state, values, rewards, log_probs, entropy_term):
        """
        Update function
        :return:
        """

        # extract the Qval of the final state
        _, Qval, _, _ = self.select_action(final_state)

        # compute Q values
        Qvals = np.zeros_like(values).astype(np.float)
        for t in reversed(range(len(rewards))):
            Qval = rewards[t] + self.args.gamma * Qval
            Qvals[t] = Qval

        # update actor critic
        values = torch.FloatTensor(values).to(self.device)
        Qvals = torch.FloatTensor(Qvals).to(self.device)
        log_probs = torch.stack(log_probs).to(self.device)

        advantage = Qvals - values
        actor_loss = (-log_probs * advantage).mean()
        critic_loss = 0.5 * advantage.pow(2).mean()
        ac_loss = actor_loss + critic_loss + 0.001 * entropy_term

        self.optimizer.zero_grad()
        ac_loss.backward(retain_graph=True)
        self.optimizer.step()

