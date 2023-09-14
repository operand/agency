function getAppEnv() {
  if (typeof window !== 'undefined' && window.APP_ENV) {
    return window.APP_ENV;
  }
  return 'production';
}

if (getAppEnv() === 'development') {
  console.log("development mode loaded");
}

// TODO: agency-js client library
