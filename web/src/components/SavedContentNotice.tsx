import { Link } from 'react-router';
import { useT } from '../i18n';

export function SavedContentNotice({ onRestart }: { onRestart: () => void }) {
  const t = useT();
  return <div className="stack">
    <h1>{t('recovery.contentTitle')}</h1>
    <p>{t('recovery.contentMessage')}</p>
    <Link className="btn" to="/settings">{t('recovery.backup')}</Link>
    <button type="button" className="btn btn-primary" onClick={onRestart}>{t('recovery.restart')}</button>
  </div>;
}
