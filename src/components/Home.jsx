import { usePosts } from '../lib/usePosts.js';
import Composer from './Composer.jsx';
import Feed from './Feed.jsx';

export default function Home({ me }) {
  const { posts, error, reload } = usePosts();
  return (
    <>
      <Composer me={me} onPosted={reload} />
      <Feed posts={posts} error={error} me={me} onChange={reload} />
    </>
  );
}
