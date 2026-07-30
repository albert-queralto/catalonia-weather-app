import { createTheme } from "@mui/material/styles";

export const appTheme = createTheme({
  palette: {
    mode: "light",
    primary: {
      main: "#1769aa",
      dark: "#0f4c81",
      light: "#6aa9d8",
      contrastText: "#ffffff",
    },
    secondary: {
      main: "#0f766e",
      dark: "#0b5f59",
      light: "#5fb7aa",
      contrastText: "#ffffff",
    },
    success: {
      main: "#2f855a",
    },
    warning: {
      main: "#d97706",
    },
    error: {
      main: "#c2413a",
    },
    background: {
      default: "#f4f8f6",
      paper: "#fffefa",
    },
    text: {
      primary: "#17212b",
      secondary: "#5d6d7b",
    },
    divider: "rgba(36, 54, 66, 0.12)",
  },
  shape: {
    borderRadius: 8,
  },
  typography: {
    fontFamily:
      'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    h1: {
      fontWeight: 800,
    },
    h2: {
      fontWeight: 800,
    },
    h3: {
      fontWeight: 750,
    },
    h4: {
      fontWeight: 750,
    },
    h5: {
      fontWeight: 700,
    },
    h6: {
      fontWeight: 700,
    },
    button: {
      fontWeight: 700,
      textTransform: "none",
    },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          background:
            "linear-gradient(180deg, #f7fbfa 0%, #f4f8f6 42%, #eef4f2 100%)",
        },
      },
    },
    MuiButton: {
      defaultProps: {
        disableElevation: true,
      },
      styleOverrides: {
        root: {
          minHeight: 40,
          borderRadius: 8,
          boxShadow: "none",
        },
        containedPrimary: {
          background: "linear-gradient(135deg, #1769aa 0%, #0f766e 100%)",
          "&:hover": {
            boxShadow: "0 12px 24px rgba(23, 105, 170, 0.22)",
          },
        },
        outlined: {
          backgroundColor: "rgba(255, 255, 255, 0.55)",
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          borderColor: "rgba(36, 54, 66, 0.12)",
          boxShadow: "0 14px 34px rgba(18, 38, 48, 0.08)",
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          borderRadius: 8,
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          fontWeight: 700,
        },
      },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          backgroundColor: "rgba(255, 255, 255, 0.72)",
        },
      },
    },
  },
});
