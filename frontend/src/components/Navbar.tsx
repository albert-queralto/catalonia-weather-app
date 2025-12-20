import { AppBar, Toolbar, Typography, Button, Box } from '@mui/material';
import { Link } from 'react-router-dom';

export default function Navbar() {
  return (
    <AppBar position="static" color="primary">
      <Toolbar>
        <Typography variant="h6" sx={{ flexGrow: 1, marginLeft: 5 }}>
          Catalunya Weather App
        </Typography>
        <Box>
          <Button color="inherit" component={Link} to="/populate">
            Populate Data
          </Button>
          <Button color="inherit" component={Link} to="/historical">
            Dades històriques
          </Button>
          <Button color="inherit" component={Link} to="/forecast">
            Productes prediccions
          </Button>
          <Button color="inherit" component={Link} to="/modeling">
            Modelització
          </Button>
        </Box>
      </Toolbar>
    </AppBar>
  );
}