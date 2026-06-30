type Props = {
  progress: number;
  stage: string;
};

export function ProgressBar({ progress, stage }: Props) {
  return (
    <div className="progress-wrap">
      <div className="progress-header">
        <span>{stage}</span>
        <span>{progress}%</span>
      </div>
      <div className="progress-track">
        <div className="progress-fill" style={{ width: `${progress}%` }} />
      </div>
    </div>
  );
}
