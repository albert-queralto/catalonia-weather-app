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
            Historical Data
          </Button>
          <Button color="inherit" component={Link} to="/air-quality-map">
            Air Quality Map
          </Button>
          <Button color="inherit" component={Link} to="/episodis-oberts">
            Current Alerts
          </Button>
          <Button color="inherit" component={Link} to="/ml-model-trainer">
            Model Training
          </Button>
          {/* <Button color="inherit" component={Link} to="/forecast">
            Forecast Products
          </Button> */}
        </Box>
      </Toolbar>
    </AppBar>
  );
}