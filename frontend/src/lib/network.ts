export const isMobile = () => {
  if (typeof window === "undefined") return false;
  return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(
    window.navigator.userAgent
  );
};

export const getBackendStatus = async (apiUrl: string) => {
  try {
    const res = await fetch(`${apiUrl}/healthz`, { 
        method: "GET",
        signal: AbortSignal.timeout(2000) 
    });
    return res.ok;
  } catch (e) {
    return false;
  }
};

export const getLocalIP = () => {
    // This is just a helper to remind the user of the expected local IP pattern
    return "192.168.1.100"; 
};
