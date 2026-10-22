import { createBrowserRouter, RouterProvider, useRouteError } from "react-router";
import { Layout } from "./components/Layout";
import { About } from "./pages/About";
import { AuthFinish } from "./pages/AuthFinish";
import { Flashcards } from "./pages/Flashcards";
import { Encounters } from "./pages/Encounters";
import { EncounterPlayer } from "./pages/EncounterPlayer";
import { Home } from "./pages/Home";
import { Hub } from "./pages/Hub";
import { ItemDetail } from "./pages/ItemDetail";
import { LessonPage } from "./pages/Lesson";
import { NotFound } from "./pages/NotFound";
import { PracticeHome, PracticeSession } from "./pages/Practice";
import { ProgressPage } from "./pages/ProgressPage";
import { Reference } from "./pages/Reference";
import { ReviewPage } from "./pages/ReviewPage";
import { Settings } from "./pages/Settings";

function RouteError() {
  const error = useRouteError();
  console.error(error);
  return (
    <main id="main" className="main stack" role="alert">
      <h1>문제가 생겼습니다 · Something went wrong</h1>
      <p>화면을 표시하지 못했습니다. 저장된 학습 기록은 그대로입니다. · The page could not be displayed. Your saved progress has not been changed.</p>
      <p>
        <a className="btn btn-primary" href="/">
          처음 화면으로 · Start page
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
      { path: "encounters", element: <Encounters /> },
      { path: "encounters/:scenarioId", element: <EncounterPlayer /> },
      { path: "chp/lessons/:lessonId", element: <LessonPage /> },
      { path: "chp/flashcards", element: <Flashcards /> },
      { path: "chp/practice", element: <PracticeHome /> },
      { path: "chp/practice/session", element: <PracticeSession /> },
      { path: "chp/reference", element: <Reference /> },
      { path: "chp/items/:itemId", element: <ItemDetail /> },
      { path: "progress", element: <ProgressPage /> },
      { path: "about", element: <About /> },
      { path: "review", element: <ReviewPage /> },
      { path: "settings", element: <Settings /> },
      { path: "auth/finish", element: <AuthFinish /> },
      { path: "*", element: <NotFound /> },
    ],
  },
];

export function App() {
  return <RouterProvider router={createBrowserRouter(routes)} />;
}
