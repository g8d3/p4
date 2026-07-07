import { Composition } from "remotion";
import { TalkingHead } from "./TalkingHead";
import { Podcast } from "./Podcast";
import { CodeReview } from "./CodeReview";
import { Timeline } from "./Timeline";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="talking-head"
        component={TalkingHead}
        durationInFrames={30 * 30}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{
          title: "The Debugging Journey: 30s to 3.5s",
        }}
      />
      <Composition
        id="podcast"
        component={Podcast}
        durationInFrames={45 * 30}
        fps={30}
        width={1080}
        height={1920}
      />
      <Composition
        id="code-review"
        component={CodeReview}
        durationInFrames={25 * 30}
        fps={30}
        width={1080}
        height={1920}
      />
      <Composition
        id="timeline"
        component={Timeline}
        durationInFrames={20 * 30}
        fps={30}
        width={1080}
        height={1920}
      />
    </>
  );
};
