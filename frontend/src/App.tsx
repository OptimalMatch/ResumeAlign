import React, { useState } from 'react';
import {
  Container,
  Typography,
  Box,
  TextField,
  Button,
  Paper,
  Alert,
  CircularProgress,
  Card,
  CardContent,
  Chip,
  Stack,
  List,
  ListItem,
  ListItemText,
  Divider,
  Tab,
  Tabs,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  ToggleButtonGroup,
  ToggleButton,
} from '@mui/material';
import { CloudUpload, Send, CheckCircle, Info, ExpandMore, Work, Link, Description } from '@mui/icons-material';
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || '';

interface OptimizationResult {
  id: string;
  optimized_resume: string;
  suggestions: string[];
  match_score: number;
  created_at: string;
  job_posting_content: string;
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`simple-tabpanel-${index}`}
      aria-labelledby={`simple-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

function App() {
  const [jobInputType, setJobInputType] = useState<'url' | 'text'>('text');
  const [jobUrl, setJobUrl] = useState('');
  const [jobText, setJobText] = useState('');
  const [resumeText, setResumeText] = useState('');
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<OptimizationResult | null>(null);
  const [tabValue, setTabValue] = useState(0);
  const [history, setHistory] = useState<OptimizationResult[]>([]);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
    if (newValue === 1) {
      fetchHistory();
    }
  };

  const fetchHistory = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/optimizations`);
      setHistory(response.data);
    } catch (err) {
      console.error('Failed to fetch history', err);
    }
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files[0]) {
      setResumeFile(event.target.files[0]);
      setResumeText(''); // Clear text when file is selected
    }
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError('');
    setResult(null);

    try {
      const formData = new FormData();

      // Add job posting information based on input type
      if (jobInputType === 'url') {
        formData.append('job_url', jobUrl);
      } else {
        formData.append('job_text', jobText);
      }

      if (resumeFile) {
        formData.append('resume_file', resumeFile);
      } else if (resumeText) {
        formData.append('resume_text', resumeText);
      } else {
        throw new Error('Please provide either a resume file or text');
      }

      const response = await axios.post(`${API_BASE_URL}/optimize`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      console.log('API Response:', response.data);
      console.log('Job posting content:', response.data.job_posting_content);
      console.log('Job posting content length:', response.data.job_posting_content?.length);
      setResult(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const getMatchScoreColor = (score: number) => {
    if (score >= 0.8) return 'success';
    if (score >= 0.6) return 'warning';
    return 'error';
  };

  return (
    <Container maxWidth="lg">
      <Box sx={{ my: 4 }}>
        <Typography variant="h3" component="h1" gutterBottom align="center">
          Resume Optimizer
        </Typography>
        <Typography variant="subtitle1" align="center" color="text.secondary" gutterBottom>
          Optimize your resume for any job posting using AI
        </Typography>

        <Box sx={{ borderBottom: 1, borderColor: 'divider', mt: 4 }}>
          <Tabs value={tabValue} onChange={handleTabChange} aria-label="basic tabs">
            <Tab label="Optimize Resume" />
            <Tab label="History" />
          </Tabs>
        </Box>

        <TabPanel value={tabValue} index={0}>
          <Paper elevation={3} sx={{ p: 4, mt: 3 }}>
            <form onSubmit={handleSubmit}>
              <Stack spacing={3}>
                <Box>
                  <Typography variant="h6" gutterBottom>
                    Job Posting Input
                  </Typography>
                  <ToggleButtonGroup
                    value={jobInputType}
                    exclusive
                    onChange={(e, newType) => {
                      if (newType !== null) {
                        setJobInputType(newType);
                        setJobUrl('');
                        setJobText('');
                      }
                    }}
                    fullWidth
                    sx={{ mb: 2 }}
                  >
                    <ToggleButton value="text">
                      <Description sx={{ mr: 1 }} />
                      Paste Job Text
                    </ToggleButton>
                    <ToggleButton value="url">
                      <Link sx={{ mr: 1 }} />
                      Job URL
                    </ToggleButton>
                  </ToggleButtonGroup>

                  {jobInputType === 'url' ? (
                    <TextField
                      fullWidth
                      label="Job Posting URL"
                      variant="outlined"
                      value={jobUrl}
                      onChange={(e) => setJobUrl(e.target.value)}
                      required
                      placeholder="https://example.com/job-posting"
                      helperText="Note: Some job sites may block automated access"
                    />
                  ) : (
                    <TextField
                      fullWidth
                      multiline
                      rows={8}
                      label="Job Posting Content"
                      variant="outlined"
                      value={jobText}
                      onChange={(e) => setJobText(e.target.value)}
                      required
                      placeholder="Paste the full job posting content here..."
                      helperText="Recommended: Copy/paste the entire job description to avoid bot blocking"
                    />
                  )}
                </Box>

                <Box>
                  <Typography variant="h6" gutterBottom>
                    Resume Input
                  </Typography>
                  <Box sx={{ mb: 2 }}>
                    <Button
                      variant="outlined"
                      component="label"
                      startIcon={<CloudUpload />}
                      fullWidth
                    >
                      Upload Resume (PDF or TXT)
                      <input
                        type="file"
                        hidden
                        accept=".pdf,.txt"
                        onChange={handleFileChange}
                      />
                    </Button>
                    {resumeFile && (
                      <Typography variant="body2" sx={{ mt: 1 }}>
                        Selected: {resumeFile.name}
                      </Typography>
                    )}
                  </Box>

                  <Typography variant="body1" align="center" sx={{ my: 2 }}>
                    OR
                  </Typography>

                  <TextField
                    fullWidth
                    multiline
                    rows={6}
                    label="Paste Resume Text"
                    variant="outlined"
                    value={resumeText}
                    onChange={(e) => {
                      setResumeText(e.target.value);
                      setResumeFile(null); // Clear file when text is entered
                    }}
                    placeholder="Paste your resume content here..."
                  />
                </Box>

                <Button
                  type="submit"
                  variant="contained"
                  size="large"
                  fullWidth
                  disabled={loading || (jobInputType === 'url' ? !jobUrl : !jobText) || (!resumeFile && !resumeText)}
                  startIcon={loading ? <CircularProgress size={20} /> : <Send />}
                >
                  {loading ? 'Optimizing...' : 'Optimize Resume'}
                </Button>
              </Stack>
            </form>

            {error && (
              <Alert severity="error" sx={{ mt: 3 }}>
                {error}
              </Alert>
            )}
          </Paper>

          {result && (
            <Box sx={{ mt: 4 }}>
              <Card>
                <CardContent>
                  <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                    <Typography variant="h5">
                      Optimization Results
                    </Typography>
                    <Chip
                      label={`Match Score: ${(result.match_score * 100).toFixed(0)}%`}
                      color={getMatchScoreColor(result.match_score)}
                      icon={<CheckCircle />}
                    />
                  </Stack>

                  <Divider sx={{ my: 2 }} />

                  <Typography variant="h6" gutterBottom>
                    <Info /> Suggestions
                  </Typography>
                  <List>
                    {result.suggestions.map((suggestion, index) => (
                      <ListItem key={index}>
                        <ListItemText primary={suggestion} />
                      </ListItem>
                    ))}
                  </List>

                  <Divider sx={{ my: 2 }} />

                  {(() => {
                    console.log('Rendering result:', result);
                    console.log('Job posting content in render:', result.job_posting_content);
                    return null;
                  })()}
                  {result.job_posting_content && (
                    <Accordion defaultExpanded>
                      <AccordionSummary expandIcon={<ExpandMore />}>
                        <Typography variant="h6">
                          <Work sx={{ mr: 1, verticalAlign: 'middle' }} />
                          Job Posting Content
                        </Typography>
                      </AccordionSummary>
                      <AccordionDetails>
                        <Paper variant="outlined" sx={{ p: 2, backgroundColor: '#f9f9f9', maxHeight: '300px', overflow: 'auto' }}>
                          <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                            {result.job_posting_content || 'No content available'}
                          </Typography>
                        </Paper>
                      </AccordionDetails>
                    </Accordion>
                  )}

                  <Divider sx={{ my: 2 }} />

                  <Typography variant="h6" gutterBottom>
                    Optimized Resume
                  </Typography>
                  <Paper variant="outlined" sx={{ p: 2, backgroundColor: '#f5f5f5' }}>
                    <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
                      {result.optimized_resume}
                    </Typography>
                  </Paper>

                  <Box sx={{ mt: 2 }}>
                    <Button
                      variant="contained"
                      onClick={() => {
                        const blob = new Blob([result.optimized_resume], { type: 'text/plain' });
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = 'optimized_resume.txt';
                        a.click();
                      }}
                    >
                      Download Optimized Resume
                    </Button>
                  </Box>
                </CardContent>
              </Card>
            </Box>
          )}
        </TabPanel>

        <TabPanel value={tabValue} index={1}>
          <Typography variant="h5" gutterBottom>
            Optimization History
          </Typography>
          {history.length === 0 ? (
            <Typography color="text.secondary">No optimization history yet.</Typography>
          ) : (
            <Stack spacing={2}>
              {history.map((item) => (
                <Card key={item.id}>
                  <CardContent>
                    <Stack direction="row" justifyContent="space-between" alignItems="center">
                      <Typography variant="h6">
                        Optimization from {new Date(item.created_at).toLocaleString()}
                      </Typography>
                      <Chip
                        label={`Score: ${(item.match_score * 100).toFixed(0)}%`}
                        color={getMatchScoreColor(item.match_score)}
                        size="small"
                      />
                    </Stack>
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                      {item.suggestions.length} suggestions provided
                    </Typography>
                  </CardContent>
                </Card>
              ))}
            </Stack>
          )}
        </TabPanel>
      </Box>
    </Container>
  );
}

export default App;