import React from 'react';
import { Composition } from 'remotion';
import { MainVideo } from './Scene';
export const RemotionRoot: React.FC = () => (
  <Composition id="MainVideo" component={MainVideo} durationInFrames={65*30} fps={30} width={608} height={1080} />
);
