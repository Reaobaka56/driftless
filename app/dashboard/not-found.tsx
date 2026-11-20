import Link from 'next/link';
import { Empty } from './_components/ui';

export default function NotFound() {
  return (
    <div className="plate">
      <Empty title="Not found">
        That record doesn’t exist, or the link is malformed. <Link href="/dashboard/scans">Back to scans</Link>
      </Empty>
    </div>
  );
}
