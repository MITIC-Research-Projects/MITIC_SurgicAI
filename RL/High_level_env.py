# Training environment for approaching stage for (DDPG+HER)

import gymnasium as gym
from gymnasium import spaces
import numpy as np
import time
import re
from Low_env_init_nonHierarchy import low_level_controller
from evaluation import *


def add_break(s):
    time.sleep(s)
    # print('-------------')

class SRC_high_level(gym.Env):
    """Custom Environment that follows gym interface"""
    metadata = {'render.modes': ['human'],"reward_type":['dense']}

    def seed(self, seed=None):
        self.np_random, seed = gym.utils.seeding.np_random(seed)
        return [seed]

    def __init__(self):
        super(SRC_high_level, self).__init__()
        # 定义动作空间为两个离散动作 {0, 1}
        self.action_space = spaces.Discrete(5)
        
        # 定义观测空间为21维，每个维度的值范围从负无穷大到正无穷大
        self.observation_space = spaces.Box(
            low=np.array([-np.inf] * 35, dtype=np.float32),
            high=np.array([np.inf] * 35, dtype=np.float32),
            shape=(35,),
            dtype=np.float32
        )
        self.LLC = low_level_controller()
        self.low_env = self.LLC.env
        self.scale_factor = np.array([100, 100, 100, 1, 1, 1, 1])
        return

    def reset(self, **kwargs):
        self.timer = 0
        self.task_idx_test = 1
        self.obs_low,self.info = self.low_env.reset()

        psm1_pos = self.low_env.psm1.get_T_b_w()*convert_mat_to_frame(self.low_env.psm1.measured_cp())
        psm2_pos = self.low_env.psm2.get_T_b_w()*convert_mat_to_frame(self.low_env.psm2.measured_cp())
        needle_pos = self.low_env.needle_kin.get_bm_pose()
        psm1_jaw = self.low_env.psm_goal_list[0][-1]
        psm2_jaw = self.low_env.psm_goal_list[1][-1]
        psm1_obs = np.concatenate((self.low_env.Frame2Vec(psm1_pos),np.array([psm1_jaw])))*self.scale_factor 
        psm2_obs = np.concatenate((self.low_env.Frame2Vec(psm2_pos),np.array([psm2_jaw])))*self.scale_factor 
        needle_obs = np.concatenate((self.low_env.Frame2Vec(needle_pos),np.array([0.0])))*self.scale_factor
        psm1_needle_world = needle_obs-psm1_obs
        psm2_needle_world = needle_obs-psm2_obs
        self.obs = np.concatenate((psm1_obs,psm2_obs,needle_obs,psm1_needle_world,psm2_needle_world),dtype=np.float32)
        
        return self.obs, self.info
    
    # def step(self, action):
        
    #     if (self.timer%100 == 0 or self.low_env.subtask_completion == 1):
    #         task_idx = action+1

    #     # Uncomment for hard rule high level policy test
    #     # if (self.timer%20 == 0):
    #     #     if self.low_env.subtask_completion == 1:
    #     #         self.task_idx_test = self.task_idx_test+1
            
    #         self.low_env.task_update(task_idx)

    #     next_obs_low, _, self.terminate, self.truncate, self.info = self.LLC.low_level_step(self.obs_low)
    #     self.obs_low = next_obs_low

    #     needle_obs = self.low_env.needle_goal_evaluator(0.010)
    #     current = self.obs_low['observation'][0:6]
    #     self.obs = np.concatenate((current,needle_obs,needle_obs-current), dtype=np.float32)
    #     self.reward = float(int(self.terminate)*10)
    #     self.timer+=1
    #     return self.obs, self.reward, self.terminate, self.truncate, self.info
    
    def step(self, action):
        subtimer = 0
        task_idx = action+1
        self.low_env.task_update(task_idx)

        # Completion prior
        while (self.low_env.subtask_completion == 0):
            next_obs_low, _, self.terminate, self.truncate, self.info = self.LLC.low_level_step(self.obs_low)
            self.obs_low = next_obs_low
            subtimer += 1
            if (subtimer>200):
                break

        # # Timer prior
        # while (subtimer<30):
        #     next_obs_low, _, self.terminate, self.truncate, self.info = self.LLC.low_level_step(self.obs_low)
        #     self.obs_low = next_obs_low
        #     subtimer += 1
        #     if self.low_env.subtask_completion == 1:
        #         time.sleep(0.1)
        #         break

        
        psm1_pos = self.low_env.psm1.get_T_b_w()*convert_mat_to_frame(self.low_env.psm1.measured_cp())
        psm2_pos = self.low_env.psm2.get_T_b_w()*convert_mat_to_frame(self.low_env.psm2.measured_cp())
        needle_pos = self.low_env.needle_kin.get_bm_pose()
        psm1_jaw = self.low_env.psm_goal_list[0][-1]
        psm2_jaw = self.low_env.psm_goal_list[1][-1]
        psm1_obs = np.concatenate((self.low_env.Frame2Vec(psm1_pos),np.array([psm1_jaw])))*self.scale_factor 
        psm2_obs = np.concatenate((self.low_env.Frame2Vec(psm2_pos),np.array([psm2_jaw])))*self.scale_factor 
        needle_obs = np.concatenate((self.low_env.Frame2Vec(needle_pos),np.array([0.0])))*self.scale_factor
        psm1_needle_world = needle_obs-psm1_obs
        psm2_needle_world = needle_obs-psm2_obs
        self.obs = np.concatenate((psm1_obs,psm2_obs,needle_obs,psm1_needle_world,psm2_needle_world),dtype=np.float32)

        self.reward = float(int(self.terminate)*10)
        self.timer+=1

        # # #################################################
        # ## Uncomment for hard rule high level policy test
        # subtimer = 0
        # while subtimer<40:
        #     if self.low_env.subtask_completion == 1:
        #         self.task_idx_test = self.task_idx_test+1
        #         self.low_env.task_update(self.task_idx_test)
        #         break
        #     self.low_env.task_update(self.task_idx_test)
        #     next_obs_low, _, self.terminate, self.truncate, self.info = self.LLC.low_level_step(self.obs_low)
            
        #     # trans_error = np.linalg.norm(self.obs_low['observation'][14:17])
        #     # angle_error = np.linalg.norm(self.obs_low['observation'][17:20])
        #     # print(f"trans_error:{trans_error}, angle_error:{angle_error}")
                  
        #     # time.sleep(0.1)
        #     self.obs_low = next_obs_low
        #     subtimer+=1
        
        # needle_obs = self.low_env.needle_goal_evaluator(0.010)*np.array([100,100,100,1,1,1,1])
        # needle_obs = needle_obs[0:-1]
        # current = self.obs_low['observation'][0:6]
        # self.obs = np.concatenate((current,needle_obs,needle_obs-current), dtype=np.float32)
        # self.reward = float(int(self.terminate)*10)

        # relative_obs = self.obs[14:]
        # print(f"vector:{relative_obs}, norm:{np.linalg.norm(relative_obs)}")

        return self.obs, self.reward, self.terminate, self.truncate, self.info
    
    def render(self, mode='human', close=False):
        pass