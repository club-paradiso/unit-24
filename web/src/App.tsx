import { createBrowserRouter, RouterProvider, useRouteError } from "react-router";
import { Layout } from "./components/Layout";
import { About } from "./pages/About";
import { Flashcards } from "./pages/Flashcards";
import { Home } from "./pages/Home";
import { Hub } from "./pages/Hub";
import { ItemDetail } from "./pages/ItemDetail";
import { LessonPage } from "./pages/Lesson";
import { NotFound } from "./pages/NotFound";
import { PracticeHome, PracticeSession } from "./pages/Practice";
import { ProgressPage } from "./pages/ProgressPage";
import { Reference } from "./pages/Reference";

function RouteError() {
  const error = useRouteError();
  console.error(error);
  return (
    <main id="main" className="main stack" role="alert">
      <h1>Something went wrong</h1>
      <p>The page could not be displayed. Your saved progress has not been changed.</p>
      <p>
        <a className="btn btn-primary" href="/">
          Go to the start page
        </a>
      </p>
    </main>
  );
}

export const routes = [
  {
    path: "/",
    element: <Layout />,
    errorElement: <RouteError />,
    children: [
      { index: true, element: <Home /> },
      { path: "chp", element: <Hub /> },
      { path: "chp/lessons/:lessonId", element: <LessonPage /> },
      { path: "chp/flashcards", element: <Flashcards /> },
      { path: "chp/practice", element: <PracticeHome /> },
      { path: "chp/practice/session", element: <PracticeSession /> },
      { path: "chp/reference", element: <Reference /> },
      { path: "chp/items/:itemId", element: <ItemDetail /> },
      { path: "progress", element: <ProgressPage /> },
      { path: "about", element: <About /> },
      { path: "*", element: <NotFound /> },
    ],
  },
];

export function App() {
  return <RouterProvider router={createBrowserRouter(routes)} />;
}
